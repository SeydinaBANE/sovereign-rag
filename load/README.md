# Load testing (k6)

Reproducible load test for the query path, used to size pods and calibrate the HPA
on measured numbers rather than guesses.

## What it does

[`k6/rag_query.js`](k6/rag_query.js) ingests a small corpus once (`setup`), then ramps
virtual users hammering `POST /query`:

- Ramp: 0 → 10 VUs (20s) → 50 VUs (40s) → 0 (20s).
- Thresholds (the run **fails** if breached): `http_req_failed < 1%`, and `p95` latency
  on `/query` `< 1000ms`.

Defaults run against the offline app (fake providers), so it measures the **framework /
threadpool overhead**, not LLM/Qdrant latency. Point it at a real deployment to measure
end-to-end capacity.

## Run

```bash
# 1. Start the API (offline defaults need no keys)
make run            # uvicorn on :8000   (or: make up for the full stack)

# 2. In another shell, run the load test
make load                                  # against http://localhost:8000
make load BASE_URL=https://srag.example.eu # against a deployment
```

Auth-enabled targets: pass an API key with the `ingest`+`query` permissions:

```bash
SRAG_API_KEY=acme-key make load BASE_URL=https://srag.example.eu
```

Requires [k6](https://k6.io/docs/get-started/installation/) (`brew install k6`).

## Reading the results & calibrating the HPA

- `http_req_duration p(95)` on `{endpoint:query}` — your latency SLO indicator.
- `http_reqs` rate and `iterations` — throughput (req/s) at the sustained VU level.
- Watch where p95 starts climbing as VUs rise: that VU count is the **saturation point
  per pod**. Set the HPA `targetCPUUtilizationPercentage` so a pod scales out *before*
  that point, and set `minReplicas` for your baseline RPS.
- A single uvicorn worker is bounded by the FastAPI threadpool; prefer more replicas
  (HPA) over a single large pod. `WEB_CONCURRENCY>1` only with the Postgres audit/vault
  backends (see [`../docs/operations.md`](../docs/operations.md)).

> Tip: run twice — once against fake providers (framework ceiling) and once against the
> real Mistral/Qdrant stack (true end-to-end) — to separate app overhead from provider latency.
