from __future__ import annotations

from sovereign_rag.domain.models import SparseVector


class FastEmbedSparse:
    """Self-hostable sparse encoder via fastembed (e.g. BM25, SPLADE)."""

    def __init__(self, model: str = "Qdrant/bm25") -> None:
        from fastembed import SparseTextEmbedding

        self._model = SparseTextEmbedding(model_name=model)

    def encode(self, texts: list[str]) -> list[SparseVector]:
        return [
            SparseVector(
                indices=[int(index) for index in embedding.indices],
                values=[float(value) for value in embedding.values],
            )
            for embedding in self._model.embed(texts)
        ]
