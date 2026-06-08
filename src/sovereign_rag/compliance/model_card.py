from __future__ import annotations

from sovereign_rag.domain.models import ModelCard, RiskLevel

_UNACCEPTABLE = ("social scoring", "mass surveillance", "subliminal", "manipulation")
_HIGH = ("recruitment", "hiring", "credit", "scoring", "medical", "health", "justice", "biometric")
_LIMITED = ("chatbot", "assistant", "rag", "summariz", "question answering", "search assistant")

_DEFAULT_MITIGATIONS = (
    "PII masking at ingestion and on input/output",
    "Citation-grounded answers with refusal when context is insufficient",
    "Hash-chained append-only audit log",
    "Data-residency enforcement at retrieval time",
    "Prompt-injection input guardrail",
    "Automated groundedness/relevance evaluations",
)


def classify_risk(purpose: str) -> RiskLevel:
    lowered = purpose.lower()
    if any(keyword in lowered for keyword in _UNACCEPTABLE):
        return RiskLevel.UNACCEPTABLE
    if any(keyword in lowered for keyword in _HIGH):
        return RiskLevel.HIGH
    if any(keyword in lowered for keyword in _LIMITED):
        return RiskLevel.LIMITED
    return RiskLevel.MINIMAL


def build_card(
    system_name: str,
    purpose: str,
    llm_model: str,
    embedding_model: str,
    data_sources: list[str],
    regions: list[str],
    eval_scores: dict[str, float] | None = None,
) -> ModelCard:
    risk = classify_risk(purpose)
    mitigations = list(_DEFAULT_MITIGATIONS)
    if risk is RiskLevel.HIGH:
        mitigations.append("Human-oversight checkpoint required before action")
    return ModelCard(
        system_name=system_name,
        purpose=purpose,
        risk_level=risk,
        llm_model=llm_model,
        embedding_model=embedding_model,
        data_sources=data_sources,
        regions=regions,
        mitigations=mitigations,
        eval_scores=eval_scores or {},
    )
