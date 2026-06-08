from __future__ import annotations

from typing import Protocol, runtime_checkable

from sovereign_rag.domain.models import Chunk, ScoredChunk


@runtime_checkable
class LexicalIndexPort(Protocol):
    def index(self, chunks: list[Chunk]) -> None: ...

    def search(
        self,
        text: str,
        top_k: int,
        regions: list[str] | None = None,
    ) -> list[ScoredChunk]: ...

    def delete_by_source(self, source: str) -> int: ...

    def count(self) -> int: ...
