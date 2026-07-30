from __future__ import annotations

import re
import unicodedata

from sovereign_rag.compliance import pii
from sovereign_rag.config import PIIPolicy
from sovereign_rag.domain.models import GuardrailResult, PIIFinding

_INJECTION_PHRASES = [
    r"ignore (?:all |the )?(?:previous|above|prior|earlier) (?:instructions|prompts|rules)",
    r"disregard (?:all |the )?(?:previous|prior|above) (?:instructions|rules|context)",
    r"forget (?:all |everything |the )?(?:previous|above|prior|earlier)",
    r"(?:reveal|show|print|repeat|expose) (?:your )?(?:system )?(?:prompt|instructions)",
    r"override (?:the )?(?:system|rules|instructions|guardrails)",
    r"you are now",
    r"system prompt",
    r"new instructions",
    r"developer mode",
    r"jailbreak",
    r"do anything now",
    r"\bdan\b",
]
_INJECTION_PATTERNS = [re.compile(phrase) for phrase in _INJECTION_PHRASES]


def _normalize(text: str) -> str:
    folded = unicodedata.normalize("NFKC", text).casefold()
    stripped = "".join(ch for ch in folded if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", stripped).strip()


class RegexGuardrail:
    """Dependency-free PII + prompt-injection guardrail (sovereign default)."""

    def __init__(self, pii_policy: PIIPolicy = PIIPolicy.MASK) -> None:
        self._policy = pii_policy

    def scan_input(self, text: str) -> GuardrailResult:
        injection = self._detect_injection(text)
        sanitized, findings = pii.mask(text)
        if injection:
            return GuardrailResult(
                allowed=False,
                sanitized_text=sanitized,
                pii=findings,
                injection_detected=True,
                reason="Potential prompt injection detected.",
            )
        return self._apply_pii_policy(text, sanitized, findings)

    def scan_output(self, text: str) -> GuardrailResult:
        sanitized, findings = pii.mask(text)
        return self._apply_pii_policy(text, sanitized, findings)

    def _apply_pii_policy(
        self,
        original: str,
        sanitized: str,
        findings: list[PIIFinding],
    ) -> GuardrailResult:
        if not findings:
            return GuardrailResult(allowed=True, sanitized_text=original)
        if self._policy is PIIPolicy.REFUSE:
            return GuardrailResult(
                allowed=False,
                sanitized_text=sanitized,
                pii=findings,
                reason="PII detected and policy is 'refuse'.",
            )
        if self._policy is PIIPolicy.ALLOW:
            return GuardrailResult(allowed=True, sanitized_text=original, pii=findings)
        return GuardrailResult(allowed=True, sanitized_text=sanitized, pii=findings)

    @staticmethod
    def _detect_injection(text: str) -> bool:
        normalized = _normalize(text)
        return any(pattern.search(normalized) for pattern in _INJECTION_PATTERNS)
