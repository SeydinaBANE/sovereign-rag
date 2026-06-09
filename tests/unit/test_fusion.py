from sovereign_rag.domain.models import Chunk, ScoredChunk
from sovereign_rag.services.fusion import reciprocal_rank_fusion


def _scored(chunk_id: str, score: float) -> ScoredChunk:
    chunk = Chunk(
        id=chunk_id,
        document_id="doc",
        text=chunk_id,
        source="s.md",
        region="eu-west",
        position=0,
    )
    return ScoredChunk(chunk=chunk, score=score)


def test_rrf_rewards_agreement_across_rankings():
    vector = [_scored("a", 0.9), _scored("b", 0.8)]
    lexical = [_scored("a", 5.0), _scored("c", 4.0)]
    fused = reciprocal_rank_fusion([vector, lexical], k=60)
    assert fused[0].chunk.id == "a"


def test_rrf_deduplicates_chunks():
    ranking = [_scored("a", 1.0)]
    fused = reciprocal_rank_fusion([ranking, ranking], k=60)
    assert len(fused) == 1
    assert fused[0].score == 2 * (1.0 / 61)


def test_rrf_empty_inputs_return_empty():
    assert reciprocal_rank_fusion([[], []], k=60) == []
