from __future__ import annotations

from sovereign_rag.domain.models import Chunk, ScoredChunk


def reciprocal_rank_fusion(
    rankings: list[list[ScoredChunk]],
    k: int = 60,
) -> list[ScoredChunk]:
    scores: dict[str, float] = {}
    chunks: dict[str, Chunk] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            chunk_id = item.chunk.id
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
            chunks[chunk_id] = item.chunk
    fused = [ScoredChunk(chunk=chunks[chunk_id], score=score) for chunk_id, score in scores.items()]
    fused.sort(key=lambda item: item.score, reverse=True)
    return fused
