from __future__ import annotations


class SovereignRagError(Exception):
    """Base class for all domain errors."""


class ResidencyError(SovereignRagError):
    """Raised when an operation targets a region outside the allowed perimeter."""

    def __init__(self, region: str, allowed: list[str]) -> None:
        super().__init__(f"Region '{region}' is not allowed. Allowed regions: {allowed}.")
        self.region = region
        self.allowed = allowed


class GuardrailBlockedError(SovereignRagError):
    """Raised when a guardrail policy blocks the request (e.g. PII policy=refuse)."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class EmptyCorpusError(SovereignRagError):
    """Raised when ingestion receives no usable content."""


class IndexEmptyError(SovereignRagError):
    """Raised when a query runs against an empty vector store."""
