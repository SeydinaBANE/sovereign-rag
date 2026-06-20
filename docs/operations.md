# Operations runbook

Operational procedures for running Sovereign RAG in production. Pairs with
[`deployment.md`](deployment.md) (Helm/K8s) and [`configuration.md`](configuration.md) (env knobs).

## Backup & restore

### Audit log (compliance evidence — back up first)

- **`file` provider** (`SRAG_AUDIT_PROVIDER=file`): the hash-chained log is a single append-only file
  at `SRAG_AUDIT_PATH`. Back it up with the pod's persistent volume snapshot; it is node-local, so a
  single replica only. Verify integrity any time via `GET /compliance/audit/verify` (auth: `read_compliance`).
- **`postgres` provider** (recommended for HA): the chain lives in the `audit_log` table. Use managed
  Postgres PITR / `pg_dump`. Restore is a standard DB restore; the chain re-verifies end to end.
- **Retention/rotation:** the log is unbounded by design (tamper-evidence). Archive cold segments to
  WORM/object storage per your retention policy; never edit in place (it breaks the chain).

### Vector store (Qdrant)

- Prefer a managed EU Qdrant with its own backup/snapshot schedule. For the bundled StatefulSet, snapshot
  the PVC or use Qdrant snapshots. Re-ingestion from source documents is always a fallback (idempotent:
  deterministic point IDs).

### PII vault

- **`postgres` provider** (`SRAG_PII_VAULT_PROVIDER=postgres`): back up the `pii_vault` table alongside
  the encryption secret — **ciphertext is useless without `SRAG_PII_VAULT_SECRET`/`SRAG_PII_VAULT_SALT`**.
- **`memory` provider:** non-persistent; tokens do not survive a restart. Single-replica/dev only.

## Key & secret rotation

- **`SRAG_PII_VAULT_SECRET` / `SRAG_PII_VAULT_SALT`** derive the Fernet key (PBKDF2-HMAC-SHA256). Rotating
  either makes existing ciphertext undecryptable — re-tokenize affected data during a maintenance window
  (decrypt with the old secret, re-encrypt with the new). Keep the secret in a Secret manager (Vault /
  External Secrets), never in the ConfigMap.
- **API keys / OIDC secrets:** rotate via `SRAG_API_KEYS` / `SRAG_OIDC_HS256_SECRET`; rollout restarts pods.

## Incident response

| Symptom | Likely cause | Action |
|---|---|---|
| Boot fails with a `SRAG_*` ValueError | startup validation caught an unsafe config | fix the named env var; the message states exactly what's missing |
| Requests hang then 5xx | LLM/Qdrant slow or down | timeouts + retries already bound this; check provider status, scale, or fail over |
| `GET /compliance/audit/verify` returns `false` | audit chain broken/tampered | freeze writes, snapshot the log, investigate; with multi-worker check `WEB_CONCURRENCY`/postgres audit |
| 422 `InputTooLargeError` spike | oversized/abusive payloads | confirm `SRAG_MAX_*` limits; add gateway rate limiting |
| Guardrail false positives | injection/PII patterns over-matching | tune policy (`SRAG_PII_POLICY`) or escalate to review; patterns live in `regex_guardrail.py` |

## Scaling

- Horizontal scale requires shared state: `SRAG_AUDIT_PROVIDER=postgres`, `SRAG_PII_VAULT_PROVIDER=postgres`
  (if the vault is on), and `SRAG_SPARSE_PROVIDER=fastembed` with Qdrant. See `deployment.md` → *Multi-replica / HA*.
- Per-pod concurrency is bounded by the FastAPI threadpool; raise replicas (HPA) rather than relying on a
  single large pod. `WEB_CONCURRENCY>1` only with the Postgres audit/vault backends.
- Rate limiting and TLS termination belong at the ingress/gateway, not in-app.
