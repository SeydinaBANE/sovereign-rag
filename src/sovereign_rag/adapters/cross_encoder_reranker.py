from __future__ import annotations

from sovereign_rag.domain.models import ScoredChunk


class CrossEncoderReranker:
    """Cross-encoder reranker (self-hostable, e.g. BAAI/bge-reranker)."""

    def __init__(self, model: str = "BAAI/bge-reranker-base") -> None:
        from sentence_transformers import CrossEncoder

        self._model = CrossEncoder(model)

    def rerank(
        self,
        query: str,
        candidates: list[ScoredChunk],
        top_k: int,
    ) -> list[ScoredChunk]:
        if not candidates:
            return []
        pairs = [(query, item.chunk.text) for item in candidates]
        scores = self._model.predict(pairs)
        rescored = [
            ScoredChunk(chunk=item.chunk, score=float(score))
            for item, score in zip(candidates, scores, strict=True)
        ]
        rescored.sort(key=lambda item: item.score, reverse=True)
        return rescored[:top_k]
