# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**Sovereign RAG** — a compliance-by-design RAG accelerator (Mistral LLM, Qdrant vector search,
PII masking, hash-chained audit log, data-residency guardrails, AI Act model cards, Langfuse/OTel
observability). Hexagonal architecture: every external dependency sits behind a typed **port**
(`typing.Protocol`), so providers are swappable and the package imports/tests run with **no heavy
SDKs installed and no external services** (defaults are in-memory fakes).

## Commands

Everything is driven through `make` (which wraps `uv run`):

```bash
make install      # uv sync --extra dev
make demo         # ingest sample corpus + run grounded / out-of-scope / PII queries (no keys needed)
make run          # uvicorn on http://localhost:8000/docs
make test         # pytest (unit + integration), coverage is on by default
make lint         # ruff check src tests
make typecheck    # mypy (strict)
make format       # ruff format + ruff check --fix
make up / down    # docker compose: api + qdrant + langfuse + postgres
make precommit    # pre-commit run --all-files
```

Run a single test:

```bash
uv run pytest tests/unit/test_fusion.py                         # one file
uv run pytest tests/unit/test_fusion.py::test_rrf_merges_ranks  # one test
uv run pytest -k "tenant"                                       # by keyword
```

Before returning code, the global rule applies: `make lint typecheck test` must all be green.

Helm chart (`deploy/helm/sovereign-rag`, deploys API + optional Qdrant to EU K8s) — validate with
`make helm-lint` and `make helm-template` (requires `helm`); CI also lints/renders it. EU overlays:
`values-ovhcloud.yaml`, `values-outscale.yaml`. See `docs/deployment.md`.

## Optional extras & docs

Python **>=3.11**. Heavy providers are opt-in extras (installed via `uv sync --extra <name>`);
each maps to a lazily-imported adapter, so the package stays importable without them:

`mistral` (Mistral LLM), `qdrant` (vector store), `embeddings` (fastembed sparse),
`rerank` (sentence-transformers cross-encoder), `pii` (Presidio), `observability`
(Langfuse/OTel), `auth-oidc` (PyJWT), `pii-vault` (cryptography/Fernet),
`finetune-local` (transformers/peft/trl/torch).

Deeper docs live in `docs/`: `architecture.md`, `configuration.md`, `deployment.md`,
and `compliance/`.

## Architecture (the big picture)

Dependency direction is strictly inward — **domain depends on nothing**:

```
api (FastAPI routers) → services → ports (Protocol) ← adapters (Mistral/Qdrant/Presidio/...)
                                      ↘ compliance/ + observability/ (cross-cutting, injected)
```

- **`domain/`** — pure types: `models.py` (Document, Chunk, etc.), `access.py` (Role/Permission/Principal
  + role→permission matrix), `exceptions.py` (business exceptions, raised here, caught in the API layer).
- **`ports/`** — `Protocol` interfaces only: `llm`, `embeddings`, `vector_store`, `lexical`, `sparse`,
  `reranker`, `guardrail`, `audit`, `auth`. No implementation, no SDK imports.
- **`adapters/`** — port implementations. Each heavy SDK (`mistralai`, `qdrant-client`, `presidio`,
  `fastembed`, `sentence-transformers`) is **imported lazily inside the adapter**, never at module top
  level — this is what keeps the package importable without optional deps. `fakes.py` holds the
  deterministic in-memory implementations used by default and in tests. Outbound calls (Mistral,
  Qdrant, JWKS) carry timeouts and a bounded backoff retry (`retry.py`, `SRAG_RETRY_*`).
- **`services/`** — application orchestration: `ingestion`, `retrieval`, `fusion` (Reciprocal Rank
  Fusion), `rag` (the query pipeline), `access_control`, `chunking`. Services depend only on ports.
- **`compliance/`** — cross-cutting: `pii` (mask/refuse/allow), `audit` (append-only **hash-chained**
  log behind `AuditPort`: `FileAuditLog` caches the chain tip in memory + serialises writes with a lock;
  `PostgresAuditLog` is the shared multi-replica backend, selected by `SRAG_AUDIT_PROVIDER=file|postgres`),
  `data_residency` (region filtering enforced at retrieval, not just config), `model_card`.
- **`observability/`** — `tracing` (Langfuse/OTel spans) and `evals` (automated eval scores).
- **`api/`** — FastAPI app, routers (`ingest`, `query`, `compliance`, `fine_tuning`, `pii`, `health`),
  DTO `schemas.py`, `limits.py` (request-size guardrails → `InputTooLargeError`/422, driven by
  `SRAG_MAX_*`), and `security.py` (API-key → `Principal` resolution as a FastAPI dependency).
  Probes: `/healthz` (liveness, O(1)) and `/readyz` (readiness); audit-chain integrity is verified
  on demand via `GET /compliance/audit/verify`, never on a probe. A middleware adds baseline security
  headers (HSTS, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`) and the app `lifespan`
  validates `Settings` at startup (fail-fast).

### Reversible PII vault (`services` integration, `ports/vault.py`)

`PIIVaultPort` (`InMemoryPIIVault`: deterministic per-tenant tokens, Fernet-encrypted values). Gated by
`SRAG_PII_VAULT_ON_INGEST` (default off): when on, `IngestionService` tokenizes PII instead of
destructively masking, and `RAGService` detokenizes the answer + citations for the authorized principal
(audited). Also exposed as `/pii/tokenize` (perm `ingest`) and `/pii/detokenize` (perm `manage`), both
tenant-scoped and audited.

### Fine-tuning (`services/fine_tuning.py`, `ports/fine_tuning.py`)

LoRA fine-tuning of an open-source LLM behind `FineTuningPort`, same hexagon pattern. Adapters:
`FakeFineTuner` (default, offline), `MistralFineTuner` (Mistral La Plateforme), `LocalLoRAFineTuner`
(on-prem `transformers`/`peft`/`trl`, lazy-imported; extra `finetune-local`). The service requires the
`manage` permission (admin only), scopes jobs to the principal's tenant (cross-tenant → not found), and
audits create/cancel. Provider via `SRAG_FINE_TUNING_PROVIDER` (`none|fake|mistral|local`); `none`
returns 503 on the `/fine-tuning/jobs` endpoints.

### Wiring: the Container

`container.py` is the composition root. `build_*` factories read `Settings` and select adapters by
provider enum; `Container` is a frozen dataclass holding the assembled services. Routers get it via
`Depends(get_container)`. **To add a provider:** add an enum value in `config.py`, write the adapter
(lazy SDK import), and branch on it in the relevant `build_*` factory — nothing else changes.

### Query pipeline (`services/rag.py`, mirrors `POST /query`)

authn/authz (resolve `Principal`, enforce `query` permission, scope all store access to the tenant) →
input guardrail (PII + injection) → embed → **hybrid retrieve** (dense via `VectorStorePort` + lexical
via `LexicalIndexPort`, both tenant- and region-filtered) → **fuse (RRF) + rerank** → grounding gate
(`min_score` on cosine drives refusal) → LLM generate → output guardrail → hash-chained audit append →
trace span. In `vector` retrieval mode only the dense leg runs.

## Configuration

All config is env-driven via `pydantic-settings`, prefix **`SRAG_`** (see `.env.example` for every knob).
Defaults run fully offline: `SRAG_LLM_PROVIDER=fake`, `SRAG_VECTOR_PROVIDER=memory`,
`SRAG_EMBEDDING_PROVIDER=fake`, `SRAG_AUTH_ENABLED=false`. Provider enums live in `config.py`.
A `@model_validator` on `Settings` **refuses to boot** on unsafe combinations (auth on without
credentials, Mistral provider without an API key, vault on with a weak secret, `postgres` audit
without a DSN, empty `allowed_regions`) — fail fast at startup, not on the first request.

- **Auth off** → every request is a single local `admin` principal on `SRAG_DEFAULT_TENANT`.
- **Auth on** → resolved via the pluggable `PrincipalResolverPort` (selected by `SRAG_AUTH_PROVIDER`):
  - `static` → API key (header `x-api-key` or `Authorization: Bearer`) matched against JSON
    `SRAG_API_KEYS` (`StaticPrincipalResolver`).
  - `oidc` → `Authorization: Bearer <JWT>` validated by `OidcPrincipalResolver` (issuer JWKS for
    RS256 or `SRAG_OIDC_HS256_SECRET` for HS256); claims mapped to tenant/roles via
    `SRAG_OIDC_*_CLAIM` (dotted paths supported, e.g. Keycloak `realm_access.roles`). Invalid/expired
    tokens → 401. Wire new providers in `build_principals` (`container.py`).
  - Roles: `admin | editor | viewer` (permission matrix in `domain/access.py`). **Tenant isolation is
    a hard filter** at every store access — tenants can never read each other's data; preserve this
    when touching retrieval/ingestion.
- **Hybrid on Qdrant**: with `SRAG_VECTOR_PROVIDER=qdrant` + `SRAG_SPARSE_PROVIDER=fastembed`, sparse
  vectors are Qdrant-native (one collection, named dense + sparse vectors — fully persistent). With
  `memory`, lexical is the in-process BM25 index (`adapters/bm25.py`).

## Conventions (enforced)

- **Strict typing everywhere** — mypy `strict`, `disallow_any_generics`. Annotate all params and
  returns; no bare `Any`/`dict`/`list`; no `# type: ignore` without a documented reason.
- **Ruff**, line length **100**, rule set includes `ANN` (annotations) and `B`/`SIM`/`RUF`. Tests are
  exempt from annotation rules (`tests/**`).
- **No comments in code** (self-documenting) — this is a global project rule.
- `pytest` uses `asyncio_mode = auto`; new tests mirror the `tests/unit` + `tests/integration` split and
  use the fakes, not live services. Name tests `test_<function>_<case>`.
