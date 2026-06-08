from __future__ import annotations

from typing import Protocol, runtime_checkable

from sovereign_rag.domain.models import SparseVector


@runtime_checkable
class SparseEmbeddingPort(Protocol):
    def encode(self, texts: list[str]) -> list[SparseVector]: ...
