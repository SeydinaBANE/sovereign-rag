from __future__ import annotations

from sovereign_rag.domain.models import ScoredChunk
from sovereign_rag.text import tokenize


class LexicalReranker:
    """Deterministic, dependency-free reranker by query-term coverage."""

    def rerank(
        self,
        query: str,
        candidates: list[ScoredChunk],
        top_k: int,
    ) -> list[ScoredChunk]:
        query_terms = set(tokenize(query))
        if not query_terms:
            return candidates[:top_k]
        rescored = [
            ScoredChunk(chunk=item.chunk, score=self._coverage(query_terms, item))
            for item in candidates
        ]
        rescored.sort(key=lambda item: item.score, reverse=True)
        return rescored[:top_k]

    @staticmethod
    def _coverage(query_terms: set[str], item: ScoredChunk) -> float:
        document_terms = set(tokenize(item.chunk.text))
        return len(query_terms & document_terms) / len(query_terms)
