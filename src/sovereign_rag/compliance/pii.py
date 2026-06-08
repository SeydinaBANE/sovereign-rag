from __future__ import annotations

import re
from re import Pattern

from sovereign_rag.domain.models import PIIEntityType, PIIFinding

_PATTERNS: dict[PIIEntityType, Pattern[str]] = {
    PIIEntityType.EMAIL: re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    PIIEntityType.IBAN: re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]){11,30}\b"),
    PIIEntityType.CREDIT_CARD: re.compile(r"\b(?:\d[ -]?){13,16}\b"),
    PIIEntityType.PHONE: re.compile(r"\b(?:\+\d{1,3}[ .-]?)?(?:\d[ .-]?){9,12}\b"),
}

_MASK = "[REDACTED:{kind}]"


def detect(text: str) -> list[PIIFinding]:
    findings: list[PIIFinding] = []
    for entity_type, pattern in _PATTERNS.items():
        for match in pattern.finditer(text):
            findings.append(
                PIIFinding(entity_type=entity_type, start=match.start(), end=match.end())
            )
    return _dedupe(findings)


def mask(text: str) -> tuple[str, list[PIIFinding]]:
    findings = detect(text)
    if not findings:
        return text, []
    ordered = sorted(findings, key=lambda f: f.start, reverse=True)
    masked = text
    for finding in ordered:
        replacement = _MASK.format(kind=finding.entity_type.value)
        masked = masked[: finding.start] + replacement + masked[finding.end :]
    return masked, findings


def _dedupe(findings: list[PIIFinding]) -> list[PIIFinding]:
    findings = sorted(findings, key=lambda f: (f.start, -(f.end)))
    kept: list[PIIFinding] = []
    last_end = -1
    for finding in findings:
        if finding.start >= last_end:
            kept.append(finding)
            last_end = finding.end
    return kept
