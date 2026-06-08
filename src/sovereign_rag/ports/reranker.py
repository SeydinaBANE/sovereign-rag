from __future__ import annotations

from typing import Protocol, runtime_checkable

from sovereign_rag.domain.models import ScoredChunk


@runtime_checkable
class RerankerPort(Protocol):
    def rerank(
        self,
        query: str,
        candidates: list[ScoredChunk],
        top_k: int,
    ) -> list[ScoredChunk]: ...
