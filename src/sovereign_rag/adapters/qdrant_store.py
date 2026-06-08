from __future__ import annotations

import uuid

from sovereign_rag.domain.models import Chunk, EmbeddedChunk, ScoredChunk


class QdrantStore:
    """Self-hostable Qdrant vector store with region-aware filtering."""

    def __init__(self, url: str, collection: str, dim: int) -> None:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams

        self._collection = collection
        self._client = QdrantClient(url=url)
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
                payload=self._payload(item.chunk),
            )
            for item in items
        ]
        self._client.upsert(collection_name=self._collection, points=points)

    def search(
        self,
        embedding: list[float],
        top_k: int,
        regions: list[str] | None = None,
    ) -> list[ScoredChunk]:
        from qdrant_client.models import FieldCondition, Filter, MatchAny

        query_filter = None
        if regions is not None:
            query_filter = Filter(must=[FieldCondition(key="region", match=MatchAny(any=regions))])
        hits = self._client.search(
            collection_name=self._collection,
            query_vector=embedding,
            limit=top_k,
            query_filter=query_filter,
            with_payload=True,
        )
        return [self._to_scored(hit) for hit in hits]

    def delete_by_source(self, source: str) -> int:
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        selector = Filter(must=[FieldCondition(key="source", match=MatchValue(value=source))])
        before = self.count()
        self._client.delete(collection_name=self._collection, points_selector=selector)
        return before - self.count()

    def count(self) -> int:
        return int(self._client.count(collection_name=self._collection).count)

    @staticmethod
    def _payload(chunk: Chunk) -> dict[str, object]:
        data = chunk.model_dump()
        data.pop("id", None)
        data["chunk_id"] = chunk.id
        return data

    @staticmethod
    def _to_scored(hit: object) -> ScoredChunk:
        payload = dict(getattr(hit, "payload", {}) or {})
        chunk = Chunk(
            id=str(payload.get("chunk_id", "")),
            document_id=str(payload.get("document_id", "")),
            text=str(payload.get("text", "")),
            source=str(payload.get("source", "")),
            region=str(payload.get("region", "")),
            position=int(payload.get("position", 0)),
            metadata={k: str(v) for k, v in dict(payload.get("metadata", {})).items()},
        )
        return ScoredChunk(chunk=chunk, score=float(getattr(hit, "score", 0.0)))
