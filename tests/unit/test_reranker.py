from sovereign_rag.adapters.lexical_reranker import LexicalReranker
from sovereign_rag.domain.models import Chunk, ScoredChunk


def _scored(chunk_id: str, text: str, score: float) -> ScoredChunk:
    chunk = Chunk(
        id=chunk_id,
        document_id="doc",
        text=text,
        source="s.md",
        region="eu-west",
        position=0,
    )
    return ScoredChunk(chunk=chunk, score=score)


def test_reranker_promotes_higher_query_coverage():
    candidates = [
        _scored("low", "unrelated finance receipts", 0.99),
        _scored("high", "remote work policy three days", 0.01),
    ]
    reranked = LexicalReranker().rerank("remote work policy", candidates, top_k=2)
    assert reranked[0].chunk.id == "high"


def test_reranker_respects_top_k():
    candidates = [
        _scored("1", "remote work", 0.5),
        _scored("2", "remote policy", 0.4),
        _scored("3", "work policy", 0.3),
    ]
    reranked = LexicalReranker().rerank("remote work policy", candidates, top_k=1)
    assert len(reranked) == 1


def test_reranker_empty_query_keeps_candidates():
    candidates = [_scored("1", "remote work", 0.5)]
    reranked = LexicalReranker().rerank("", candidates, top_k=5)
    assert reranked == candidates
