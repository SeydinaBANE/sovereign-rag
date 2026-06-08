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

1. **Guardrail (input)** — scan for prompt injection + PII (policy: mask / refuse / allow).
2. **Embed** the (sanitized) query via `EmbeddingPort`.
3. **Retrieve** top-k chunks via `VectorStorePort`, filtered by allowed regions and `min_score`.
4. **Ground** — build a citation-constrained prompt; if no chunk passes `min_score`, **refuse**.
5. **Generate** via `LLMPort`.
6. **Guardrail (output)** — scan generated answer.
7. **Audit** — append a hash-chained record (query hash, sources, region, decision).
8. **Trace** — emit span (latency, tokens, cost, eval scores) to Langfuse/OTel.

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
