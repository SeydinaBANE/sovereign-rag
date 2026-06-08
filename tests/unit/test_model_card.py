from sovereign_rag.compliance.model_card import build_card, classify_risk
from sovereign_rag.domain.models import RiskLevel


def test_classify_limited_risk_for_rag_assistant():
    assert classify_risk("A RAG assistant for internal docs") is RiskLevel.LIMITED


def test_classify_high_risk_for_recruitment():
    assert classify_risk("Automated recruitment screening") is RiskLevel.HIGH


def test_classify_unacceptable_risk():
    assert classify_risk("Citizen social scoring system") is RiskLevel.UNACCEPTABLE


def test_build_card_adds_oversight_for_high_risk():
    card = build_card(
        system_name="hr-bot",
        purpose="recruitment screening",
        llm_model="mistral-large-latest",
        embedding_model="mistral-embed",
        data_sources=["cv.pdf"],
        regions=["eu-west"],
    )
    assert card.risk_level is RiskLevel.HIGH
    assert any("oversight" in mitigation.lower() for mitigation in card.mitigations)
