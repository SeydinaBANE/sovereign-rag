from sovereign_rag.adapters.bm25 import BM25Index
from sovereign_rag.domain.models import Chunk


def _chunk(chunk_id: str, text: str, region: str = "eu-west") -> Chunk:
    return Chunk(
        id=chunk_id,
        document_id="doc",
        text=text,
        source=f"{chunk_id}.md",
        region=region,
        position=0,
    )


def test_bm25_ranks_exact_term_match_first():
    index = BM25Index()
    index.index(
        [
            _chunk("1", "remote work policy three days per week"),
            _chunk("2", "expense receipts reimbursement finance team"),
        ]
    )
    results = index.search("remote work policy", top_k=2, tenant_id="default")
    assert results[0].chunk.id == "1"
    assert results[0].score > 0


def test_bm25_returns_empty_for_unknown_terms():
    index = BM25Index()
    index.index([_chunk("1", "remote work policy")])
    assert index.search("quantum chromodynamics", top_k=5, tenant_id="default") == []


def test_bm25_region_filter():
    index = BM25Index()
    index.index([_chunk("1", "data retention policy", region="eu-central")])
    assert index.search("data retention", top_k=5, tenant_id="default", regions=["eu-west"]) == []


def test_bm25_delete_by_source():
    index = BM25Index()
    index.index([_chunk("1", "alpha beta")])
    assert index.delete_by_source("1.md") == 1
    assert index.count() == 0
