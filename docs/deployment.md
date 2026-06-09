# Deployment — sovereign Kubernetes (OVHcloud / Outscale)

The Helm chart in [`deploy/helm/sovereign-rag`](../deploy/helm/sovereign-rag) deploys the API onto
any EU managed Kubernetes cluster, with an optional self-hosted Qdrant for full data residency.

## Quick start

```bash
helm lint deploy/helm/sovereign-rag
helm upgrade --install srag deploy/helm/sovereign-rag -n sovereign-rag --create-namespace
kubectl -n sovereign-rag port-forward svc/srag-sovereign-rag 8000:80
```

Defaults are offline/sovereign (fake providers, in-memory store), so the chart renders and runs with
no external dependencies. Wire real providers via `config`/`secrets`.

## EU region overlays

```bash
# OVHcloud Managed Kubernetes (region pinned, Qdrant + Langfuse + OIDC + Mistral)
helm upgrade --install srag deploy/helm/sovereign-rag \
  -f deploy/helm/sovereign-rag/values-ovhcloud.yaml

# Outscale (SecNumCloud) Kubernetes
helm upgrade --install srag deploy/helm/sovereign-rag \
  -f deploy/helm/sovereign-rag/values-outscale.yaml
```

Both overlays pin pods to an EU region via `nodeSelector` (`topology.kubernetes.io/region`), enable
the HPA, a PodDisruptionBudget, TLS ingress, and the bundled persistent Qdrant.

## Configuration

| Concern | Where |
|---|---|
| Non-secret `SRAG_*` env | `config` map → rendered into a ConfigMap |
| Secret `SRAG_*` env (Mistral key, OIDC secret, Langfuse keys) | `secrets.data` (templated Secret) **or** `secrets.existingSecret` (pre-created) |
| Replicas / autoscaling | `replicaCount`, `autoscaling.*` |
| Self-hosted Qdrant | `qdrant.enabled` (StatefulSet + PVC); auto-sets `SRAG_VECTOR_PROVIDER`/`SRAG_QDRANT_URL` |
| Data residency | `nodeSelector`, `SRAG_ALLOWED_REGIONS`, `SRAG_DEFAULT_REGION` |
| Ingress / TLS | `ingress.*` |

**Never** put secrets in `config` (it becomes a ConfigMap). Prefer `secrets.existingSecret` referencing
a Secret managed by your secrets operator (e.g. External Secrets, Vault).

## Container image

The chart points at `ghcr.io/seydinabane/sovereign-rag` (tag defaults to the chart `appVersion`).
Images are built multi-arch (`linux/amd64`, `linux/arm64`) and pushed to GHCR by the
`Publish image` workflow on every `v*.*.*` tag / published release (or manually via
**Actions → Publish image → Run workflow** with a tag).

## Notes

- Probes hit `/healthz` (liveness + readiness); readiness reflects vector-store reachability.
- Pods run non-root (`runAsNonRoot`, dropped capabilities), matching the Dockerfile `appuser`.
- A managed Qdrant (OVHcloud/Outscale) is preferred over the bundled StatefulSet for production HA —
  set `qdrant.enabled=false` and point `config.SRAG_QDRANT_URL` at the managed endpoint.
- Mistral runs via Mistral La Plateforme (FR) or a self-hosted vLLM for full on-prem; local embeddings
  (`SRAG_EMBEDDING_PROVIDER=local`) keep data inside the cluster.
