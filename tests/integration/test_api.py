from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from sovereign_rag.api.app import create_app
from sovereign_rag.container import Container, get_container


@pytest.fixture
def client(container: Container) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_container] = lambda: container
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_healthz_reports_status(client: TestClient):
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["audit_chain_valid"] is True


def test_ingest_then_query_flow(client: TestClient):
    ingest = client.post(
        "/ingest",
        json={
            "documents": [
                {
                    "id": "remote",
                    "text": "Employees may work remotely up to three days per week.",
                    "source": "remote.md",
                }
            ]
        },
    )
    assert ingest.status_code == 200
    assert ingest.json()["chunks_indexed"] >= 1

    query = client.post("/query", json={"text": "How many days remote per week?"})
    assert query.status_code == 200
    assert query.json()["refused"] is False


def test_query_empty_index_returns_conflict(client: TestClient):
    response = client.post("/query", json={"text": "anything"})
    assert response.status_code == 409


def test_compliance_card_endpoint(client: TestClient):
    response = client.get("/compliance/card")
    assert response.status_code == 200
    assert response.json()["risk_level"] == "limited"


def test_ingest_rejects_foreign_region(client: TestClient):
    response = client.post(
        "/ingest",
        json={
            "documents": [{"id": "x", "text": "hello world", "source": "x.md", "region": "us-east"}]
        },
    )
    assert response.status_code == 422
