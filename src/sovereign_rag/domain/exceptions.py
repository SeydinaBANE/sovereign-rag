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


class InputTooLargeError(SovereignRagError):
    """Raised when a request exceeds the configured input-size limits."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class AuthenticationError(SovereignRagError):
    """Raised when a request carries no valid credential."""


class AuthorizationError(SovereignRagError):
    """Raised when a principal lacks a required permission or tenant access."""


class EmptyCorpusError(SovereignRagError):
    """Raised when ingestion receives no usable content."""


class IndexEmptyError(SovereignRagError):
    """Raised when a query runs against an empty vector store."""


class FineTuningDataError(SovereignRagError):
    """Raised when a fine-tuning dataset is empty or below the minimum size."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class FineTuningJobNotFound(SovereignRagError):
    """Raised when a fine-tuning job is unknown or owned by another tenant."""

    def __init__(self, job_id: str) -> None:
        super().__init__(f"Fine-tuning job '{job_id}' was not found.")
        self.job_id = job_id


class FineTuningDisabledError(SovereignRagError):
    """Raised when fine-tuning is requested while no provider is configured."""

    def __init__(self) -> None:
        super().__init__("Fine-tuning is disabled (SRAG_FINE_TUNING_PROVIDER=none).")
