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
from sovereign_rag.domain.access import Role


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(
        llm_provider=LLMProvider.FAKE,
        embedding_provider=EmbeddingProvider.FAKE,
        vector_provider=VectorProvider.MEMORY,
        embedding_dim=512,
        min_score=0.18,
        auth_enabled=True,
        audit_path=str(tmp_path / "audit.log"),
        allowed_regions=["eu-west"],
        default_region="eu-west",
        api_keys=[
            ApiKeyPrincipal(key="editor", subject="e", tenant_id="acme", roles=[Role.EDITOR]),
            ApiKeyPrincipal(key="viewer", subject="v", tenant_id="acme", roles=[Role.VIEWER]),
        ],
    )
    container = build_container(settings)
    app = create_app()
    app.dependency_overrides[get_container] = lambda: container
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _ingest(client: TestClient, key: str) -> object:
    return client.post(
        "/ingest",
        headers={"X-API-Key": key},
        json={
            "documents": [
                {"id": "a", "text": "remote work policy three days per week", "source": "a.md"}
            ]
        },
    )


def test_request_without_key_is_unauthorized(client: TestClient):
    assert client.post("/query", json={"text": "anything"}).status_code == 401


def test_invalid_key_is_unauthorized(client: TestClient):
    response = client.post("/query", headers={"X-API-Key": "nope"}, json={"text": "anything"})
    assert response.status_code == 401


def test_viewer_cannot_ingest(client: TestClient):
    assert _ingest(client, "viewer").status_code == 403


def test_editor_can_ingest_then_viewer_can_query(client: TestClient):
    assert _ingest(client, "editor").status_code == 200
    response = client.post(
        "/query", headers={"X-API-Key": "viewer"}, json={"text": "remote work policy"}
    )
    assert response.status_code == 200
    assert response.json()["refused"] is False
