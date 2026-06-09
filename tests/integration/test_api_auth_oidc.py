import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import jwt
import pytest
from fastapi.testclient import TestClient

from sovereign_rag.api.app import create_app
from sovereign_rag.config import (
    AuthProvider,
    EmbeddingProvider,
    LLMProvider,
    Settings,
    VectorProvider,
)
from sovereign_rag.container import build_container, get_container

_SECRET = "integration-test-secret-key-at-least-32-bytes"
_ISSUER = "https://issuer.example.eu"
_AUDIENCE = "sovereign-rag"


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(
        llm_provider=LLMProvider.FAKE,
        embedding_provider=EmbeddingProvider.FAKE,
        vector_provider=VectorProvider.MEMORY,
        embedding_dim=512,
        min_score=0.18,
        auth_enabled=True,
        auth_provider=AuthProvider.OIDC,
        oidc_issuer=_ISSUER,
        oidc_audience=_AUDIENCE,
        oidc_algorithms=["HS256"],
        oidc_hs256_secret=_SECRET,
        audit_path=str(tmp_path / "audit.log"),
        allowed_regions=["eu-west"],
        default_region="eu-west",
    )
    container = build_container(settings)
    app = create_app()
    app.dependency_overrides[get_container] = lambda: container
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _token(roles: list[str], tenant: str = "acme") -> str:
    payload: dict[str, Any] = {
        "sub": "user",
        "tenant_id": tenant,
        "roles": roles,
        "aud": _AUDIENCE,
        "iss": _ISSUER,
        "exp": int(time.time()) + 300,
    }
    return jwt.encode(payload, _SECRET, algorithm="HS256")


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_no_token_is_unauthorized(client: TestClient) -> None:
    assert client.post("/query", json={"text": "anything"}).status_code == 401


def test_invalid_token_is_unauthorized(client: TestClient) -> None:
    response = client.post("/query", headers=_bearer("garbage"), json={"text": "anything"})
    assert response.status_code == 401


def test_editor_can_ingest_then_query(client: TestClient) -> None:
    document = {"id": "a", "text": "remote work three days per week", "source": "a.md"}
    ingest = client.post(
        "/ingest",
        headers=_bearer(_token(["editor"])),
        json={"documents": [document]},
    )
    assert ingest.status_code == 200
    response = client.post(
        "/query", headers=_bearer(_token(["viewer"])), json={"text": "remote work"}
    )
    assert response.status_code == 200
    assert response.json()["refused"] is False


def test_viewer_cannot_ingest(client: TestClient) -> None:
    response = client.post(
        "/ingest",
        headers=_bearer(_token(["viewer"])),
        json={"documents": [{"id": "a", "text": "x", "source": "a.md"}]},
    )
    assert response.status_code == 403
