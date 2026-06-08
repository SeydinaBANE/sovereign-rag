# AI Act / GDPR / Data Act — regulatory-to-technical mapping

This document is the bridge a consulting engagement needs: it translates regulatory
obligations into the concrete technical controls implemented in this codebase.

## 1. EU AI Act — risk classification

The accelerator ships a rule-based classifier (`compliance/model_card.py`) that maps a
use case to a risk tier and the controls it triggers.

| Risk tier | Examples | Obligations enforced here |
|---|---|---|
| **Unacceptable** | social scoring, manipulation | classifier flags → deployment blocked |
| **High** | recruitment, credit, health, justice | model card + audit log + human oversight hooks + eval thresholds |
| **Limited** | chatbots, RAG assistants | transparency notice + citation grounding + audit log |
| **Minimal** | search, internal Q&A | baseline logging |

A typical enterprise RAG assistant lands in **Limited risk** → transparency + traceability.

## 2. Obligation → control matrix

| Obligation (AI Act / GDPR / Data Act) | Technical control | Location |
|---|---|---|
| Transparency: user knows it is AI | API response carries `is_ai_generated` + citations | `api/schemas.py`, `services/rag.py` |
| Grounding / no fabrication | refusal when no chunk ≥ `min_score` | `services/rag.py` |
| Record-keeping & traceability (Art. 12) | hash-chained append-only audit log | `compliance/audit.py` |
| Data minimisation (GDPR Art. 5) | PII masked at ingestion and on I/O | `compliance/pii.py` |
| Right to erasure (GDPR Art. 17) | delete-by-source on the vector store | `ports/vector_store.py` (`delete`) |
| Data residency / sovereignty (Data Act) | region tag per chunk + retrieval filter + config guard | `compliance/data_residency.py` |
| Security / prompt-injection resistance | input + output guardrails | `adapters/presidio_guardrail.py`, `services/rag.py` |
| Technical documentation (Annex IV) | auto-generated model card | `compliance/model_card.py` |
| Accuracy monitoring (Art. 15) | automated eval harness (groundedness/relevance) | `observability/evals.py` |

## 3. Model card

`GET /compliance/card` returns a structured card: system name, purpose, models used,
data sources, residency, eval scores, risk tier, and applied mitigations — exportable
as the technical-documentation artefact regulators expect.

## 4. Residual responsibilities (out of scope of code)

- DPIA (Data Protection Impact Assessment) — organisational.
- Human oversight procedures for high-risk deployments — organisational + UI.
- Conformity assessment & CE marking for high-risk systems — legal.

These are intentionally left to the engagement; the code provides the **evidence and
controls** they rely on.
