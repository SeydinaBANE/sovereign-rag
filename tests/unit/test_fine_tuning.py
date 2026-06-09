from pathlib import Path

import pytest

from sovereign_rag.adapters.fakes import FakeFineTuner
from sovereign_rag.compliance.audit import FileAuditLog
from sovereign_rag.config import Settings
from sovereign_rag.domain.access import Principal, Role
from sovereign_rag.domain.exceptions import (
    AuthorizationError,
    FineTuningDataError,
    FineTuningJobNotFound,
)
from sovereign_rag.domain.models import (
    ChatMessage,
    FineTuningHyperParams,
    FineTuningStatus,
    TrainingExample,
)
from sovereign_rag.services.fine_tuning import FineTuningService


def _examples(count: int) -> list[TrainingExample]:
    return [
        TrainingExample(
            messages=[
                ChatMessage(role="user", content=f"question {index}"),
                ChatMessage(role="assistant", content=f"answer {index}"),
            ]
        )
        for index in range(count)
    ]


def _hyper() -> FineTuningHyperParams:
    return FineTuningHyperParams(epochs=1, learning_rate=1e-4, suffix="test")


@pytest.fixture
def service(tmp_path: Path) -> FineTuningService:
    settings = Settings(
        audit_path=str(tmp_path / "audit.log"),
        fine_tuning_min_examples=2,
        fine_tuning_base_model="open-mistral-7b",
        default_region="eu-west",
    )
    return FineTuningService(FakeFineTuner(), FileAuditLog(settings.audit_path), settings)


@pytest.fixture
def admin() -> Principal:
    return Principal(subject="alice", tenant_id="acme", roles=[Role.ADMIN])


def test_create_succeeds_and_is_audited(service: FineTuningService, admin: Principal) -> None:
    job = service.create(_examples(2), _hyper(), admin)
    assert job.status is FineTuningStatus.SUCCEEDED
    assert job.fine_tuned_model == "open-mistral-7b:test"
    assert job.tenant_id == "acme"
    assert service._audit.verify_chain() is True


def test_create_below_minimum_raises(service: FineTuningService, admin: Principal) -> None:
    with pytest.raises(FineTuningDataError):
        service.create(_examples(1), _hyper(), admin)


def test_create_with_empty_messages_raises(service: FineTuningService, admin: Principal) -> None:
    examples = [TrainingExample(messages=[]), TrainingExample(messages=[])]
    with pytest.raises(FineTuningDataError):
        service.create(examples, _hyper(), admin)


def test_viewer_cannot_fine_tune(service: FineTuningService) -> None:
    viewer = Principal(subject="bob", tenant_id="acme", roles=[Role.VIEWER])
    with pytest.raises(AuthorizationError):
        service.create(_examples(2), _hyper(), viewer)


def test_list_is_tenant_scoped(service: FineTuningService, admin: Principal) -> None:
    service.create(_examples(2), _hyper(), admin)
    other = Principal(subject="carol", tenant_id="globex", roles=[Role.ADMIN])
    assert service.list_jobs(admin) != []
    assert service.list_jobs(other) == []


def test_get_across_tenant_is_not_found(service: FineTuningService, admin: Principal) -> None:
    job = service.create(_examples(2), _hyper(), admin)
    other = Principal(subject="carol", tenant_id="globex", roles=[Role.ADMIN])
    with pytest.raises(FineTuningJobNotFound):
        service.get(job.id, other)


def test_cancel_transitions_to_cancelled(service: FineTuningService, admin: Principal) -> None:
    job = service.create(_examples(2), _hyper(), admin)
    cancelled = service.cancel(job.id, admin)
    assert cancelled.status is FineTuningStatus.CANCELLED


def test_fake_fine_tuner_unknown_job_raises() -> None:
    with pytest.raises(FineTuningJobNotFound):
        FakeFineTuner().get_job("missing")
