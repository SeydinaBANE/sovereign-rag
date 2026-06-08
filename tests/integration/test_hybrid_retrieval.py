from pathlib import Path

from sovereign_rag.config import (
    EmbeddingProvider,
    LLMProvider,
    RerankerProvider,
    RetrievalMode,
    Settings,
    VectorProvider,
)
from sovereign_rag.container import Container, build_container
from sovereign_rag.domain.models import Document, Query


def _settings(tmp_path: Path, mode: RetrievalMode, reranker: RerankerProvider) -> Settings:
    return Settings(
        llm_provider=LLMProvider.FAKE,
        embedding_provider=EmbeddingProvider.FAKE,
        vector_provider=VectorProvider.MEMORY,
        embedding_dim=512,
        min_score=0.18,
        retrieval_mode=mode,
        reranker_provider=reranker,
        top_k=2,
        audit_path=str(tmp_path / "audit.log"),
        allowed_regions=["eu-west"],
        default_region="eu-west",
    )


def test_hybrid_indexes_both_stores(container: Container, sample_documents: list[Document]):
    container.ingestion.ingest(sample_documents)
    assert container.store.count() == container.lexical.count()


def test_hybrid_respects_top_k(tmp_path: Path):
    container = build_container(_settings(tmp_path, RetrievalMode.HYBRID, RerankerProvider.LEXICAL))
    container.ingestion.ingest(
        [
            Document(
                id="a",
                text="remote work policy three days per week",
                source="a.md",
                region="eu-west",
            ),
            Document(
                id="b",
                text="remote work requires manager approval and vpn",
                source="b.md",
                region="eu-west",
            ),
            Document(
                id="c",
                text="remote work equipment provided by it team",
                source="c.md",
                region="eu-west",
            ),
        ]
    )
    results = container.retrieval.retrieve(Query(text="remote work policy"))
    assert 0 < len(results) <= 2


def test_vector_mode_without_reranker(tmp_path: Path):
    container = build_container(_settings(tmp_path, RetrievalMode.VECTOR, RerankerProvider.NONE))
    assert container.reranker is None
    container.ingestion.ingest(
        [Document(id="a", text="remote work policy three days", source="a.md", region="eu-west")]
    )
    results = container.retrieval.retrieve(Query(text="remote work policy"))
    assert results
    assert all(item.score >= 0.18 for item in results)
