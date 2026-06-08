from __future__ import annotations

import re

from sovereign_rag.compliance import pii
from sovereign_rag.config import PIIPolicy
from sovereign_rag.domain.models import GuardrailResult, PIIFinding

_INJECTION_PATTERNS = [
    re.compile(r"ignore (?:all |the )?(?:previous|above) instructions", re.IGNORECASE),
    re.compile(r"disregard (?:all |the )?(?:previous|prior) (?:instructions|rules)", re.IGNORECASE),
    re.compile(r"you are now", re.IGNORECASE),
    re.compile(r"system prompt", re.IGNORECASE),
    re.compile(r"reveal (?:your )?(?:system )?(?:prompt|instructions)", re.IGNORECASE),
]


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
        return any(pattern.search(text) for pattern in _INJECTION_PATTERNS)
