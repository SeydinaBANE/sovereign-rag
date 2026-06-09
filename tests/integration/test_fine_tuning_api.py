from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sovereign_rag.api.app import create_app
from sovereign_rag.config import ApiKeyPrincipal, FineTuningProvider, Settings
from sovereign_rag.container import build_container, get_container
from sovereign_rag.domain.access import Role


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(
        auth_enabled=True,
        audit_path=str(tmp_path / "audit.log"),
        fine_tuning_provider=FineTuningProvider.FAKE,
        fine_tuning_min_examples=2,
        default_region="eu-west",
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


def _example(question: str, answer: str) -> dict[str, object]:
    return {
        "messages": [
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ]
    }


_PAYLOAD = {
    "examples": [_example("hi", "hello"), _example("bye", "ciao")],
    "suffix": "support",
}


def test_create_requires_key(client: TestClient) -> None:
    assert client.post("/fine-tuning/jobs", json=_PAYLOAD).status_code == 401


def test_editor_cannot_fine_tune(client: TestClient) -> None:
    response = client.post("/fine-tuning/jobs", headers={"X-API-Key": "editor"}, json=_PAYLOAD)
    assert response.status_code == 403


def test_admin_create_list_get_cancel(client: TestClient) -> None:
    headers = {"X-API-Key": "admin"}
    created = client.post("/fine-tuning/jobs", headers=headers, json=_PAYLOAD)
    assert created.status_code == 200
    job_id = created.json()["id"]
    assert created.json()["status"] == "succeeded"

    listed = client.get("/fine-tuning/jobs", headers=headers)
    assert listed.status_code == 200
    assert [job["id"] for job in listed.json()] == [job_id]

    fetched = client.get(f"/fine-tuning/jobs/{job_id}", headers=headers)
    assert fetched.status_code == 200

    cancelled = client.post(f"/fine-tuning/jobs/{job_id}/cancel", headers=headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"


def test_create_below_minimum_is_unprocessable(client: TestClient) -> None:
    payload = {"examples": [_PAYLOAD["examples"][0]]}
    response = client.post("/fine-tuning/jobs", headers={"X-API-Key": "admin"}, json=payload)
    assert response.status_code == 422


def test_unknown_job_is_not_found(client: TestClient) -> None:
    response = client.get("/fine-tuning/jobs/missing", headers={"X-API-Key": "admin"})
    assert response.status_code == 404
