from __future__ import annotations

from pathlib import Path

import pytest

from sovereign_rag.config import (
    EmbeddingProvider,
    LLMProvider,
    Settings,
    VectorProvider,
)
from sovereign_rag.container import Container, build_container
from sovereign_rag.domain.models import Document


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        llm_provider=LLMProvider.FAKE,
        embedding_provider=EmbeddingProvider.FAKE,
        vector_provider=VectorProvider.MEMORY,
        embedding_dim=512,
        min_score=0.18,
        audit_path=str(tmp_path / "audit.log"),
        allowed_regions=["eu-west", "eu-central"],
        default_region="eu-west",
    )


@pytest.fixture
def container(settings: Settings) -> Container:
    return build_container(settings)


@pytest.fixture
def sample_documents() -> list[Document]:
    return [
        Document(
            id="remote",
            text=(
                "Acme Remote Work Policy. Employees may work remotely up to three days "
                "per week with manager approval and a secure VPN connection."
            ),
            source="remote_work_policy.md",
            region="eu-west",
        ),
        Document(
            id="retention",
            text=(
                "Acme Data Retention Policy. Customer personal data is retained for a "
                "maximum of twenty-four months and then permanently deleted under GDPR."
            ),
            source="data_retention_policy.md",
            region="eu-central",
        ),
    ]
