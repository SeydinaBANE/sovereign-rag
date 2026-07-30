import os
import uuid

import pytest

pytest.importorskip("qdrant_client")

from sovereign_rag.adapters.qdrant_store import QdrantStore
from sovereign_rag.domain.models import Chunk, EmbeddedChunk

pytestmark = pytest.mark.integration

_DIM = 8


@pytest.fixture
def store() -> QdrantStore:
    url = os.environ.get("SRAG_QDRANT_URL")
    if not url:
        pytest.skip("SRAG_QDRANT_URL not set")
    return QdrantStore(url=url, collection=f"srag_it_{uuid.uuid4().hex}", dim=_DIM)


def _embedded(chunk_id: str, tenant_id: str, region: str, vector: list[float]) -> EmbeddedChunk:
    chunk = Chunk(
        id=chunk_id,
        document_id="doc",
        text="remote work policy",
        source="policy.md",
        region=region,
        tenant_id=tenant_id,
        position=0,
    )
    return EmbeddedChunk(chunk=chunk, embedding=vector)


def test_qdrant_upsert_and_search_returns_tenant_chunk(store: QdrantStore) -> None:
    vector = [1.0] + [0.0] * (_DIM - 1)
    store.upsert([_embedded("c1", "acme", "eu-west", vector)])
    results = store.search(vector, top_k=5, tenant_id="acme")
    assert results
    assert results[0].chunk.tenant_id == "acme"
    assert results[0].chunk.id == "c1"


def test_qdrant_search_enforces_tenant_isolation(store: QdrantStore) -> None:
    vector = [1.0] + [0.0] * (_DIM - 1)
    store.upsert([_embedded("c1", "acme", "eu-west", vector)])
    assert store.search(vector, top_k=5, tenant_id="intruder") == []


def test_qdrant_search_filters_by_region(store: QdrantStore) -> None:
    vector = [1.0] + [0.0] * (_DIM - 1)
    store.upsert([_embedded("c1", "acme", "eu-west", vector)])
    assert store.search(vector, top_k=5, tenant_id="acme", regions=["eu-central"]) == []
    assert store.search(vector, top_k=5, tenant_id="acme", regions=["eu-west"])
