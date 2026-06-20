from __future__ import annotations

import uuid

from sovereign_rag.adapters.qdrant_common import (
    build_filter,
    chunk_payload,
    scored_from_hit,
)
from sovereign_rag.adapters.retry import RetryPolicy, retry_call
from sovereign_rag.domain.models import EmbeddedChunk, ScoredChunk


class QdrantStore:
    """Self-hostable Qdrant dense vector store with tenant + region filtering."""

    def __init__(
        self,
        url: str,
        collection: str,
        dim: int,
        timeout: float = 10.0,
        retry: RetryPolicy | None = None,
    ) -> None:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams

        self._collection = collection
        self._retry = retry or RetryPolicy()
        self._client = QdrantClient(url=url, timeout=int(timeout))
        if not self._client.collection_exists(collection):
            self._client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )

    def upsert(self, items: list[EmbeddedChunk]) -> None:
        from qdrant_client.models import PointStruct

        points = [
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, item.chunk.id)),
                vector=item.embedding,
                payload=chunk_payload(item.chunk),
            )
            for item in items
        ]
        retry_call(
            lambda: self._client.upsert(collection_name=self._collection, points=points),
            self._retry,
        )

    def search(
        self,
        embedding: list[float],
        top_k: int,
        tenant_id: str,
        regions: list[str] | None = None,
    ) -> list[ScoredChunk]:
        hits = retry_call(
            lambda: self._client.search(
                collection_name=self._collection,
                query_vector=embedding,
                limit=top_k,
                query_filter=build_filter(tenant_id, regions),
                with_payload=True,
            ),
            self._retry,
        )
        return [scored_from_hit(hit) for hit in hits]

    def delete_by_source(self, source: str) -> int:
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        selector = Filter(must=[FieldCondition(key="source", match=MatchValue(value=source))])
        before = self.count()
        self._client.delete(collection_name=self._collection, points_selector=selector)
        return before - self.count()

    def count(self) -> int:
        return int(self._client.count(collection_name=self._collection).count)
