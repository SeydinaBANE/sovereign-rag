# Sovereign RAG

A **sovereign, compliance-by-design RAG accelerator** for enterprise environments.

Built to demonstrate a production-grade reference architecture: **Mistral** LLM,
self-hostable **Qdrant** vector search, **PII masking**, **hash-chained audit log**,
**data-residency** guardrails, **AI Act model cards**, and **LLMOps observability**
(tracing + automated evals). Every external dependency sits behind a typed **port**,
so providers are swappable and nothing is locked to a non-sovereign vendor.

## Why this exists

| Offer requirement | Where it lives |
|---|---|
| LLM orchestration | `services/rag.py`, `ports/llm.py`, `adapters/mistral_llm.py` |
| Vector search | `services/retrieval.py`, `adapters/qdrant_store.py` |
| Hybrid search (BM25 + RRF + rerank) | `adapters/bm25.py`, `services/fusion.py`, `adapters/*_reranker.py` |
| Persistent hybrid (Qdrant sparse vectors) | `adapters/qdrant_hybrid.py`, `adapters/sparse_embeddings.py` |
| Observability / MLOps | `observability/tracing.py`, `observability/evals.py` |
| Security & guardrails | `adapters/presidio_guardrail.py`, `services/rag.py` |
| RBAC + multi-tenant isolation | `domain/access.py`, `services/access_control.py`, `api/security.py` |
| GDPR / AI Act / Data Act | `compliance/` + `docs/compliance/ai-act-mapping.md` |
| Sovereign cloud | `memory`/`qdrant` stores, local embeddings, `docker-compose.yml` |
| Reusable accelerator | hexagonal layering, ports/adapters, typed everywhere |

## Architecture

Hexagonal. The **domain** depends on nothing. **Services** depend on **ports**
(`Protocol`s). **Adapters** implement ports. Compliance and observability are
cross-cutting concerns injected into services. See [`docs/architecture.md`](docs/architecture.md).

```
API (FastAPI) -> Services -> Ports <- Adapters (Mistral / Qdrant / Presidio / ...)
                     \-> compliance/ + observability/ (cross-cutting)
```

## Quickstart (no external services)

The defaults (`SRAG_*_PROVIDER=fake/memory`) run the full pipeline with deterministic
in-memory fakes — no API keys, no Docker needed.

```bash
make install
cp .env.example .env
make demo          # ingest sample corpus, ask grounded + out-of-scope + PII questions
make test          # unit + integration
make lint typecheck
```

## Run the API

```bash
make run           # http://localhost:8000/docs
```

Key endpoints: `POST /ingest`, `POST /query`, `GET /compliance/card`, `GET /healthz`.

## Full sovereign stack (Docker)

```bash
cp .env.example .env   # set SRAG_VECTOR_PROVIDER=qdrant, SRAG_LLM_PROVIDER=mistral, keys...
make up                # api + qdrant + langfuse + postgres
```

## Configuration

All config is environment-driven via `pydantic-settings` (prefix `SRAG_`). See
[`.env.example`](.env.example) for every knob (providers, chunking, top-k, regions,
PII policy, Langfuse).

## Project status

See [`TODO.mmd`](TODO.mmd) for the build roadmap and backlog.

## License

Apache-2.0.
