# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| `0.1.x` | ✅ |
| `< 0.1` | ❌ |

## Reporting a vulnerability

Please **do not** open a public issue for security problems.

Report privately via GitHub's **Security → Report a vulnerability**
(Private Vulnerability Reporting) on this repository. Include:

- affected version / commit,
- a description and impact,
- reproduction steps or a proof of concept.

We aim to acknowledge within a few business days and to coordinate a fix and
disclosure timeline with you.

## Security posture

The accelerator is built compliance-by-design; relevant controls:

- **No hardcoded secrets** — all credentials come from `SRAG_*` environment settings;
  in Kubernetes use `secrets.existingSecret` (never the ConfigMap).
- **Hard multi-tenant isolation** — every store/vault access is tenant-scoped; cross-tenant
  reads are denied (covered by tests).
- **AuthN/AuthZ** — static API keys or JWT/OIDC bearer tokens, mapped to an RBAC model
  (`admin | editor | viewer`); invalid/expired tokens are rejected (401).
- **PII protection** — input/output guardrails (mask/refuse/allow) plus an optional reversible
  vault that tokenizes PII and encrypts values at rest (Fernet).
- **Tamper-evident audit** — append-only, hash-chained audit log for sensitive operations
  (queries, fine-tuning, detokenization).
- **Data residency** — region metadata enforced at retrieval time, not just configuration.

## Hardening checklist for deployments

- Set a strong `SRAG_PII_VAULT_SECRET` and OIDC/Mistral secrets via a secrets manager.
- Enable `SRAG_AUTH_ENABLED=true` and prefer `SRAG_AUTH_PROVIDER=oidc` in production.
- Restrict `SRAG_ALLOWED_REGIONS` to your sovereign perimeter.
- Pin workloads to EU nodes (`nodeSelector`) and terminate TLS at the ingress.
- Keep the published image (`ghcr.io/seydinabane/sovereign-rag`) up to date.
