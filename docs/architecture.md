# Architecture

## Principles

- **Hexagonal / ports & adapters.** The domain is pure; infrastructure is plugged in.
- **Sovereignty first.** Every adapter has a self-hostable or EU option; defaults run offline.
- **Compliance by design.** PII, audit, residency and documentation are first-class, not bolt-ons.
- **Swappable providers.** Mistral / Qdrant / Presidio / Langfuse are replaceable behind ports.

## Layers

```
┌──────────────────────── api (FastAPI) ─────────────────────────┐
│  routers: ingest · query · compliance · health   schemas (DTO)  │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌────────────────────── services (application) ───────────────────┐
│  IngestionService · RetrievalService · RAGService                │
└───┬────────────┬───────────────┬───────────────┬────────────────┘
    │            │               │               │
   ports (Protocol): LLMPort · EmbeddingPort · VectorStorePort · GuardrailPort · AuditPort
    │            │               │               │
┌───▼────┐  ┌────▼─────┐   ┌─────▼──────┐   ┌────▼──────┐
│ mistral│  │embeddings│   │  qdrant /  │   │ presidio /│   adapters (+ in-memory fakes)
│  / fake│  │ fake/loc.│   │  memory    │   │  regex    │
└────────┘  └──────────┘   └────────────┘   └───────────┘

cross-cutting:  compliance/ (pii · audit · data_residency · model_card)
                observability/ (tracing · evals)
```

## Request flow — `POST /query`

0. **Authenticate + authorize** — resolve the API key to a `Principal` (tenant + roles);
   enforce the `query` permission. Every downstream store access is scoped to the principal's
   tenant (hard isolation filter), so tenants can never read each other's data.
1. **Guardrail (input)** — scan for prompt injection + PII (policy: mask / refuse / allow).
2. **Embed** the (sanitized) query via `EmbeddingPort`.
3. **Hybrid retrieve** — semantic candidates via `VectorStorePort` + lexical candidates via
   `LexicalIndexPort`, both tenant- and region-filtered. A semantic relevance gate (`min_score`
   on the vector cosine) drives the refusal decision; in `vector` mode only the dense leg is used.
   Lexical backend: in-memory BM25 by default, or **Qdrant-native sparse vectors** (one collection
   with named dense + sparse vectors) when running on Qdrant — fully persistent, no in-process index.
4. **Fuse + rerank** — merge the two rankings with Reciprocal Rank Fusion, then reorder the top
   candidates via `RerankerPort` (lexical by default, optional cross-encoder).
5. **Ground** — build a citation-constrained prompt; if the gate fails, **refuse**.
6. **Generate** via `LLMPort`.
7. **Guardrail (output)** — scan generated answer.
8. **Audit** — append a hash-chained record (query hash, sources, region, decision).
9. **Trace** — emit span (latency, tokens, cost, eval scores) to Langfuse/OTel.

## Fine-tuning workstream — `POST /fine-tuning/jobs`

LoRA fine-tuning of an open-source LLM sits behind `FineTuningPort`, mirroring the rest of the
hexagon. Three adapters: deterministic in-memory **fake** (default, offline), **Mistral La
Plateforme** (sovereign EU managed LoRA), and **on-prem local LoRA/PEFT** (`transformers`/`peft`/
`trl`, imported lazily — data never leaves the cluster). `FineTuningService` enforces the `manage`
permission (admin), validates the dataset, **scopes every job to the principal's tenant** (cross-tenant
reads return *not found*), appends a hash-chained audit record (`finetune:create` / `finetune:cancel`),
and emits a trace span. Provider selected by `SRAG_FINE_TUNING_PROVIDER` (`none|fake|mistral|local`);
`none` disables the endpoints (503).

## Key design decisions (ADRs, condensed)

- **Ports as `typing.Protocol`** rather than ABCs → structural typing, zero import coupling,
  trivial in-memory fakes for fast tests.
- **Heavy SDKs imported lazily** inside adapters → the package imports and tests run without
  `mistralai`, `qdrant-client`, or `presidio` installed.
- **Append-only hash-chained audit log** → tamper-evidence for AI Act traceability without a DB.
- **Region metadata on every chunk** → data-residency enforced at retrieval time, not just config.

## Sovereign deployment (OVHcloud / Outscale)

- Qdrant, Langfuse, Postgres run as containers on managed Kubernetes (EU region).
- Mistral via Mistral La Plateforme (FR) or self-hosted `vLLM` for full on-prem.
- Embeddings local (`bge-m3` via `fastembed`) when data must never leave the cluster.
- A Helm chart is on the backlog (see `TODO.mmd`).
