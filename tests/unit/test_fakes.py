from sovereign_rag.adapters.fakes import FakeEmbedding, FakeLLM, InMemoryVectorStore
from sovereign_rag.domain.models import Chunk, EmbeddedChunk


def _embedded(chunk_id: str, text: str, region: str, embedder: FakeEmbedding) -> EmbeddedChunk:
    chunk = Chunk(
        id=chunk_id,
        document_id="doc",
        text=text,
        source="s.md",
        region=region,
        position=0,
    )
    return EmbeddedChunk(chunk=chunk, embedding=embedder.embed([text])[0])


def test_embedding_overlap_ranks_relevant_chunk_first():
    embedder = FakeEmbedding(dim=512)
    store = InMemoryVectorStore()
    store.upsert(
        [
            _embedded("1", "remote work policy three days per week", "eu-west", embedder),
            _embedded("2", "expense receipts reimbursement finance", "eu-west", embedder),
        ]
    )
    query = embedder.embed(["how many days remote work per week"])[0]
    results = store.search(query, top_k=2, tenant_id="default")
    assert results[0].chunk.id == "1"
    assert results[0].score > results[1].score


def test_store_region_filter_excludes_other_regions():
    embedder = FakeEmbedding(dim=256)
    store = InMemoryVectorStore()
    store.upsert([_embedded("1", "data retention policy", "eu-central", embedder)])
    query = embedder.embed(["data retention"])[0]
    assert store.search(query, top_k=5, tenant_id="default", regions=["eu-west"]) == []


def test_store_delete_by_source():
    embedder = FakeEmbedding(dim=64)
    store = InMemoryVectorStore()
    store.upsert([_embedded("1", "alpha", "eu-west", embedder)])
    assert store.delete_by_source("s.md") == 1
    assert store.count() == 0


def test_fake_llm_grounds_in_context():
    response = FakeLLM().complete("system", "Context:\nremote work allowed\n\nQuestion: q\n\n")
    assert "remote work allowed" in response.text
    assert response.output_tokens > 0
