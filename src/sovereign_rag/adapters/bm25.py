from __future__ import annotations

import math
from collections import Counter

from sovereign_rag.domain.models import Chunk, ScoredChunk
from sovereign_rag.text import tokenize


class BM25Index:
    """Dependency-free in-memory BM25 (Okapi) lexical index."""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self._k1 = k1
        self._b = b
        self._chunks: dict[str, Chunk] = {}
        self._tokens: dict[str, list[str]] = {}

    def index(self, chunks: list[Chunk]) -> None:
        for chunk in chunks:
            self._chunks[chunk.id] = chunk
            self._tokens[chunk.id] = tokenize(chunk.text)

    def delete_by_source(self, source: str) -> int:
        targets = [cid for cid, chunk in self._chunks.items() if chunk.source == source]
        for cid in targets:
            del self._chunks[cid]
            del self._tokens[cid]
        return len(targets)

    def count(self) -> int:
        return len(self._chunks)

    def search(
        self,
        text: str,
        top_k: int,
        tenant_id: str,
        regions: list[str] | None = None,
    ) -> list[ScoredChunk]:
        query_terms = tokenize(text)
        if not self._chunks or not query_terms:
            return []
        document_count = len(self._chunks)
        document_frequency = self._document_frequency()
        average_length = sum(len(tokens) for tokens in self._tokens.values()) / document_count

        scored: list[ScoredChunk] = []
        for cid, chunk in self._chunks.items():
            if chunk.tenant_id != tenant_id:
                continue
            if regions is not None and chunk.region not in regions:
                continue
            score = self._score(
                query_terms,
                self._tokens[cid],
                document_count,
                document_frequency,
                average_length,
            )
            if score > 0.0:
                scored.append(ScoredChunk(chunk=chunk, score=score))
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]

    def _document_frequency(self) -> Counter[str]:
        frequency: Counter[str] = Counter()
        for tokens in self._tokens.values():
            frequency.update(set(tokens))
        return frequency

    def _score(
        self,
        query_terms: list[str],
        tokens: list[str],
        document_count: int,
        document_frequency: Counter[str],
        average_length: float,
    ) -> float:
        term_frequency = Counter(tokens)
        length = len(tokens)
        score = 0.0
        for term in query_terms:
            frequency = term_frequency.get(term, 0)
            if frequency == 0:
                continue
            df = document_frequency[term]
            idf = math.log(1 + (document_count - df + 0.5) / (df + 0.5))
            denominator = frequency + self._k1 * (1 - self._b + self._b * length / average_length)
            score += idf * (frequency * (self._k1 + 1)) / denominator
        return score
