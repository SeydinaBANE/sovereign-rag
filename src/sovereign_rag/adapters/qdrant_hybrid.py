from __future__ import annotations

import uuid

from sovereign_rag.adapters.qdrant_common import (
    build_filter,
    chunk_payload,
    scored_from_hit,
)
from sovereign_rag.domain.models import Chunk, EmbeddedChunk, ScoredChunk
from sovereign_rag.ports.sparse import SparseEmbeddingPort


class QdrantHybridStore:
    """Qdrant store with named dense + sparse vectors for persistent hybrid search."""

    def __init__(
        self,
        url: str,
        collection: str,
        dim: int,
        sparse: SparseEmbeddingPort,
    ) -> None:
        from qdrant_client import QdrantClient
        from qdrant_client.models import (
            Distance,
            SparseVectorParams,
            VectorParams,
        )

        self._collection = collection
        self._sparse = sparse
        self._client = QdrantClient(url=url)
        if not self._client.collection_exists(collection):
            self._client.create_collection(
                collection_name=collection,
                vectors_config={"dense": VectorParams(size=dim, distance=Distance.COSINE)},
                sparse_vectors_config={"sparse": SparseVectorParams()},
            )

    def upsert(self, items: list[EmbeddedChunk]) -> None:
        from qdrant_client.models import PointStruct, SparseVector

        encoded = self._sparse.encode([item.chunk.text for item in items])
        points = [
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, item.chunk.id)),
                vector={
                    "dense": item.embedding,
                    "sparse": SparseVector(indices=vector.indices, values=vector.values),
                },
                payload=chunk_payload(item.chunk),
            )
            for item, vector in zip(items, encoded, strict=True)
        ]
        self._client.upsert(collection_name=self._collection, points=points)

    def search(
        self,
        embedding: list[float],
        top_k: int,
        tenant_id: str,
        regions: list[str] | None = None,
    ) -> list[ScoredChunk]:
        response = self._client.query_points(
            collection_name=self._collection,
            query=embedding,
            using="dense",
            limit=top_k,
            query_filter=build_filter(tenant_id, regions),
            with_payload=True,
        )
        return [scored_from_hit(point) for point in response.points]

    def search_sparse(
        self,
        text: str,
        top_k: int,
        tenant_id: str,
        regions: list[str] | None = None,
    ) -> list[ScoredChunk]:
        from qdrant_client.models import SparseVector

        vector = self._sparse.encode([text])[0]
        response = self._client.query_points(
            collection_name=self._collection,
            query=SparseVector(indices=vector.indices, values=vector.values),
            using="sparse",
            limit=top_k,
            query_filter=build_filter(tenant_id, regions),
            with_payload=True,
        )
        return [scored_from_hit(point) for point in response.points]

    def delete_by_source(self, source: str) -> int:
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        selector = Filter(must=[FieldCondition(key="source", match=MatchValue(value=source))])
        before = self.count()
        self._client.delete(collection_name=self._collection, points_selector=selector)
        return before - self.count()

    def count(self) -> int:
        return int(self._client.count(collection_name=self._collection).count)

    def lexical(self) -> QdrantSparseLexical:
        return QdrantSparseLexical(self)


class QdrantSparseLexical:
    """LexicalIndexPort view over a QdrantHybridStore's sparse vectors."""

    def __init__(self, store: QdrantHybridStore) -> None:
        self._store = store

    def index(self, chunks: list[Chunk]) -> None:
        return None

    def search(
        self,
        text: str,
        top_k: int,
        tenant_id: str,
        regions: list[str] | None = None,
    ) -> list[ScoredChunk]:
        return self._store.search_sparse(text, top_k, tenant_id, regions)

    def delete_by_source(self, source: str) -> int:
        return self._store.delete_by_source(source)

    def count(self) -> int:
        return self._store.count()
