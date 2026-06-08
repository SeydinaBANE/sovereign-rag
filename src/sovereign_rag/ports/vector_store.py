from __future__ import annotations

from typing import Protocol, runtime_checkable

from sovereign_rag.domain.models import EmbeddedChunk, ScoredChunk


@runtime_checkable
class VectorStorePort(Protocol):
    def upsert(self, items: list[EmbeddedChunk]) -> None: ...

    def search(
        self,
        embedding: list[float],
        top_k: int,
        tenant_id: str,
        regions: list[str] | None = None,
    ) -> list[ScoredChunk]: ...

    def delete_by_source(self, source: str) -> int: ...

    def count(self) -> int: ...
