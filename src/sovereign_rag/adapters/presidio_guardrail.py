from __future__ import annotations

from sovereign_rag.adapters.regex_guardrail import RegexGuardrail
from sovereign_rag.config import PIIPolicy
from sovereign_rag.domain.models import GuardrailResult, PIIEntityType, PIIFinding

_PRESIDIO_TO_DOMAIN = {
    "EMAIL_ADDRESS": PIIEntityType.EMAIL,
    "PHONE_NUMBER": PIIEntityType.PHONE,
    "IBAN_CODE": PIIEntityType.IBAN,
    "CREDIT_CARD": PIIEntityType.CREDIT_CARD,
    "PERSON": PIIEntityType.PERSON,
}


class PresidioGuardrail:
    """Presidio-backed PII detection; reuses RegexGuardrail for injection + policy."""

    def __init__(self, pii_policy: PIIPolicy = PIIPolicy.MASK, language: str = "en") -> None:
        from presidio_analyzer import AnalyzerEngine

        self._analyzer = AnalyzerEngine()
        self._language = language
        self._fallback = RegexGuardrail(pii_policy=pii_policy)
        self._policy = pii_policy

    def scan_input(self, text: str) -> GuardrailResult:
        base = self._fallback.scan_input(text)
        return self._merge(text, base)

    def scan_output(self, text: str) -> GuardrailResult:
        base = self._fallback.scan_output(text)
        return self._merge(text, base)

    def _merge(self, text: str, base: GuardrailResult) -> GuardrailResult:
        results = self._analyzer.analyze(text=text, language=self._language)
        extra = [
            PIIFinding(
                entity_type=_PRESIDIO_TO_DOMAIN.get(result.entity_type, PIIEntityType.OTHER),
                start=result.start,
                end=result.end,
            )
            for result in results
        ]
        merged = base.pii + extra
        return base.model_copy(update={"pii": merged})
