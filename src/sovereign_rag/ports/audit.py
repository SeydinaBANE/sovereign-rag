from __future__ import annotations

from typing import Protocol, runtime_checkable

from sovereign_rag.domain.models import AuditRecord


@runtime_checkable
class AuditPort(Protocol):
    def record(
        self,
        query_hash: str,
        sources: list[str],
        region: str,
        decision: str,
    ) -> AuditRecord: ...

    def verify_chain(self) -> bool: ...
