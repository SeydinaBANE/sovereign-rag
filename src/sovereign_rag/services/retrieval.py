from __future__ import annotations

from sovereign_rag.compliance.data_residency import filter_regions
from sovereign_rag.config import RetrievalMode, Settings
from sovereign_rag.domain.exceptions import IndexEmptyError
from sovereign_rag.domain.models import Query, ScoredChunk
from sovereign_rag.ports.embeddings import EmbeddingPort
from sovereign_rag.ports.lexical import LexicalIndexPort
from sovereign_rag.ports.reranker import RerankerPort
from sovereign_rag.ports.vector_store import VectorStorePort
from sovereign_rag.services.fusion import reciprocal_rank_fusion


class RetrievalService:
    def __init__(
        self,
        embedder: EmbeddingPort,
        store: VectorStorePort,
        lexical: LexicalIndexPort,
        settings: Settings,
        reranker: RerankerPort | None = None,
    ) -> None:
        self._embedder = embedder
        self._store = store
        self._lexical = lexical
        self._settings = settings
        self._reranker = reranker

    def retrieve(self, query: Query) -> list[ScoredChunk]:
        if self._store.count() == 0:
            raise IndexEmptyError("The vector store is empty; ingest documents first.")
        regions = filter_regions(query.regions, self._settings.allowed_regions)
        top_k = query.top_k or self._settings.top_k

        embedding = self._embedder.embed([query.text])[0]
        vector = self._store.search(embedding, self._settings.candidate_k, regions)
        if not self._is_relevant(vector):
            return []
        if self._settings.retrieval_mode is RetrievalMode.VECTOR:
            return [item for item in vector if item.score >= self._settings.min_score][:top_k]

        lexical = self._lexical.search(query.text, self._settings.candidate_k, regions)
        fused = reciprocal_rank_fusion([vector, lexical], self._settings.rrf_k)
        candidates = fused[: self._settings.rerank_candidates]
        if self._reranker is None:
            return candidates[:top_k]
        return self._reranker.rerank(query.text, candidates, top_k)

    def _is_relevant(self, vector: list[ScoredChunk]) -> bool:
        return any(item.score >= self._settings.min_score for item in vector)
