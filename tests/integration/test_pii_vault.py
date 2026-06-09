from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sovereign_rag.api.app import create_app
from sovereign_rag.config import (
    ApiKeyPrincipal,
    EmbeddingProvider,
    LLMProvider,
    Settings,
    VectorProvider,
)
from sovereign_rag.container import build_container, get_container
from sovereign_rag.domain.access import Principal, Role
from sovereign_rag.domain.models import Document, Query


def _settings(tmp_path: Path, **overrides: object) -> Settings:
    base: dict[str, object] = {
        "llm_provider": LLMProvider.FAKE,
        "embedding_provider": EmbeddingProvider.FAKE,
        "vector_provider": VectorProvider.MEMORY,
        "embedding_dim": 512,
        "min_score": 0.18,
        "audit_path": str(tmp_path / "audit.log"),
        "allowed_regions": ["eu-west"],
        "default_region": "eu-west",
        "pii_vault_on_ingest": True,
        "pii_vault_secret": "integration-vault-secret",
    }
    base.update(overrides)
    return Settings(**base)


def test_ingest_tokenizes_and_answer_is_detokenized(tmp_path: Path) -> None:
    container = build_container(_settings(tmp_path))
    document = Document(
        id="d1",
        text="Remote work approvals are sent by alice@acme.eu to all staff members.",
        source="policy.md",
        region="eu-west",
    )
    container.ingestion.ingest([document], "acme")

    stored = container.store.search([0.0] * 512, top_k=10, tenant_id="acme")
    assert all("alice@acme.eu" not in item.chunk.text for item in stored)
    assert any("[[PII:EMAIL:" in item.chunk.text for item in stored)

    answer = container.rag.answer(
        Query(text="remote work approvals staff members"),
        principal=Principal(subject="alice", tenant_id="acme", roles=[Role.ADMIN]),
    )
    assert "alice@acme.eu" in answer.text
    assert container.audit.verify_chain() is True


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    settings = _settings(
        tmp_path,
        auth_enabled=True,
        api_keys=[
            ApiKeyPrincipal(key="admin", subject="a", tenant_id="acme", roles=[Role.ADMIN]),
            ApiKeyPrincipal(key="editor", subject="e", tenant_id="acme", roles=[Role.EDITOR]),
        ],
    )
    container = build_container(settings)
    app = create_app()
    app.dependency_overrides[get_container] = lambda: container
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_tokenize_then_detokenize_via_api(client: TestClient) -> None:
    tok = client.post(
        "/pii/tokenize", headers={"X-API-Key": "editor"}, json={"text": "mail alice@acme.eu"}
    )
    assert tok.status_code == 200
    tokenized = tok.json()["text"]
    assert "alice@acme.eu" not in tokenized

    back = client.post("/pii/detokenize", headers={"X-API-Key": "admin"}, json={"text": tokenized})
    assert back.status_code == 200
    assert back.json()["text"] == "mail alice@acme.eu"


def test_editor_cannot_detokenize(client: TestClient) -> None:
    response = client.post("/pii/detokenize", headers={"X-API-Key": "editor"}, json={"text": "x"})
    assert response.status_code == 403


def test_tokenize_requires_auth(client: TestClient) -> None:
    assert client.post("/pii/tokenize", json={"text": "x"}).status_code == 401
