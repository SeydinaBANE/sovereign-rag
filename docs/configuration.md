# Configuration reference

All settings are environment-driven via `pydantic-settings`, prefixed **`SRAG_`**
(see [`src/sovereign_rag/config.py`](../src/sovereign_rag/config.py)). Defaults are
sovereign and run fully offline — no keys, no Docker. Copy [`.env.example`](../.env.example)
and override what you need.

## Providers ↔ optional dependencies

Each non-default provider needs its extra installed (`uv sync --extra <name>` or
`pip install ".[<name>]"`); heavy SDKs are imported lazily, so the package runs without them.

| Extra | Enables |
|---|---|
| `mistral` | Mistral LLM + embeddings |
| `qdrant` | Qdrant vector store |
| `embeddings` | local `fastembed` embeddings / sparse vectors |
| `rerank` | cross-encoder reranker |
| `pii` | Presidio guardrail |
| `observability` | Langfuse / OpenTelemetry tracing |
| `auth-oidc` | JWT/OIDC authentication |
| `pii-vault` | reversible PII vault (encryption) |
| `finetune-local` | on-prem LoRA/PEFT fine-tuning |

## LLM

| Variable | Default | Notes |
|---|---|---|
| `SRAG_LLM_PROVIDER` | `fake` | `fake` \| `mistral` |
| `SRAG_MISTRAL_API_KEY` | – | required for `mistral` |
| `SRAG_LLM_MODEL` | `mistral-large-latest` | |
| `SRAG_LLM_TEMPERATURE` | `0.1` | |
| `SRAG_LLM_MAX_TOKENS` | `1024` | |

## Embeddings

| Variable | Default | Notes |
|---|---|---|
| `SRAG_EMBEDDING_PROVIDER` | `fake` | `fake` \| `mistral` \| `local` |
| `SRAG_EMBEDDING_MODEL` | `mistral-embed` | HF id for `local` (e.g. `BAAI/bge-m3`) |
| `SRAG_EMBEDDING_DIM` | `1024` | must match the model |

## Vector store & hybrid retrieval

| Variable | Default | Notes |
|---|---|---|
| `SRAG_VECTOR_PROVIDER` | `memory` | `memory` \| `qdrant` |
| `SRAG_QDRANT_URL` | `http://localhost:6333` | |
| `SRAG_QDRANT_COLLECTION` | `sovereign_rag` | |
| `SRAG_SPARSE_PROVIDER` | `fastembed` | `none` \| `fastembed` (Qdrant-native sparse hybrid) |
| `SRAG_SPARSE_MODEL` | `Qdrant/bm25` | |
| `SRAG_RETRIEVAL_MODE` | `hybrid` | `vector` \| `hybrid` |
| `SRAG_CHUNK_SIZE` / `SRAG_CHUNK_OVERLAP` | `800` / `120` | |
| `SRAG_TOP_K` | `5` | results returned |
| `SRAG_MIN_SCORE` | `0.25` | relevance gate; below ⇒ refuse |
| `SRAG_CANDIDATE_K` | `20` | candidates per leg before fusion |
| `SRAG_RRF_K` | `60` | Reciprocal Rank Fusion constant |
| `SRAG_RERANKER_PROVIDER` | `lexical` | `none` \| `lexical` \| `cross_encoder` |
| `SRAG_RERANK_CANDIDATES` | `20` | |
| `SRAG_CROSS_ENCODER_MODEL` | `BAAI/bge-reranker-base` | |

## Access control & auth

| Variable | Default | Notes |
|---|---|---|
| `SRAG_AUTH_ENABLED` | `false` | `false` ⇒ single local `admin` principal |
| `SRAG_AUTH_PROVIDER` | `static` | `static` (API keys) \| `oidc` (JWT) |
| `SRAG_DEFAULT_TENANT` | `default` | |
| `SRAG_API_KEYS` | `[]` | JSON list of `{key, subject, tenant_id, roles}` |
| `SRAG_OIDC_ISSUER` | – | e.g. `https://keycloak…/realms/acme` |
| `SRAG_OIDC_AUDIENCE` | – | expected `aud` claim |
| `SRAG_OIDC_JWKS_URL` | – | defaults to `<issuer>/.well-known/jwks.json` |
| `SRAG_OIDC_ALGORITHMS` | `RS256` | comma-separated (`RS256`, `HS256`) |
| `SRAG_OIDC_HS256_SECRET` | – | HS256 only |
| `SRAG_OIDC_SUBJECT_CLAIM` | `sub` | |
| `SRAG_OIDC_TENANT_CLAIM` | `tenant_id` | dotted paths supported; falls back to default tenant |
| `SRAG_OIDC_ROLES_CLAIM` | `roles` | dotted, e.g. Keycloak `realm_access.roles` |

Roles map to `admin` \| `editor` \| `viewer` (permission matrix in `domain/access.py`).

## Compliance & PII

| Variable | Default | Notes |
|---|---|---|
| `SRAG_ALLOWED_REGIONS` | `eu-west,eu-central` | data-residency perimeter |
| `SRAG_DEFAULT_REGION` | `eu-west` | |
| `SRAG_PII_POLICY` | `mask` | `mask` \| `refuse` \| `allow` |
| `SRAG_PII_VAULT_ON_INGEST` | `false` | tokenize (reversible) instead of masking |
| `SRAG_PII_VAULT_SECRET` | – | derives the encryption key; set a strong value |
| `SRAG_AUDIT_PATH` | `data/audit/audit.log` | hash-chained audit log |

## Fine-tuning

| Variable | Default | Notes |
|---|---|---|
| `SRAG_FINE_TUNING_PROVIDER` | `fake` | `none` \| `fake` \| `mistral` \| `local` |
| `SRAG_FINE_TUNING_BASE_MODEL` | `open-mistral-7b` | HF id for `local` |
| `SRAG_FINE_TUNING_EPOCHS` | `3` | |
| `SRAG_FINE_TUNING_LEARNING_RATE` | `0.0001` | |
| `SRAG_FINE_TUNING_SUFFIX` | `sovereign` | adapter name suffix |
| `SRAG_FINE_TUNING_MIN_EXAMPLES` | `10` | dataset validation floor |
| `SRAG_FINE_TUNING_OUTPUT_DIR` | `data/fine_tuning` | `local` adapter output |

## Observability

| Variable | Default | Notes |
|---|---|---|
| `SRAG_LANGFUSE_ENABLED` | `false` | |
| `SRAG_LANGFUSE_HOST` | `http://localhost:3000` | |
| `SRAG_LANGFUSE_PUBLIC_KEY` / `SRAG_LANGFUSE_SECRET_KEY` | – | required when enabled |
