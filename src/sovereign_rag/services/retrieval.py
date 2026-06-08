from __future__ import annotations

from sovereign_rag.compliance.data_residency import filter_regions
from sovereign_rag.config import Settings
from sovereign_rag.domain.exceptions import IndexEmptyError
from sovereign_rag.domain.models import Query, ScoredChunk
from sovereign_rag.ports.embeddings import EmbeddingPort
from sovereign_rag.ports.vector_store import VectorStorePort


class RetrievalService:
    def __init__(
        self,
        embedder: EmbeddingPort,
        store: VectorStorePort,
        settings: Settings,
    ) -> None:
        self._embedder = embedder
        self._store = store
        self._settings = settings

    def retrieve(self, query: Query) -> list[ScoredChunk]:
        if self._store.count() == 0:
            raise IndexEmptyError("The vector store is empty; ingest documents first.")
        regions = filter_regions(query.regions, self._settings.allowed_regions)
        top_k = query.top_k or self._settings.top_k
        embedding = self._embedder.embed([query.text])[0]
        results = self._store.search(embedding, top_k, regions)
        return [result for result in results if result.score >= self._settings.min_score]
