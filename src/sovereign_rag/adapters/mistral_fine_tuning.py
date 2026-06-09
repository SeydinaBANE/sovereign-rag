from __future__ import annotations

import io
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sovereign_rag.domain.exceptions import FineTuningJobNotFound
from sovereign_rag.domain.models import (
    FineTuningHyperParams,
    FineTuningJob,
    FineTuningSpec,
    FineTuningStatus,
)

if TYPE_CHECKING:
    from mistralai import Mistral

_STATUS_MAP: dict[str, FineTuningStatus] = {
    "QUEUED": FineTuningStatus.PENDING,
    "VALIDATING": FineTuningStatus.PENDING,
    "VALIDATED": FineTuningStatus.PENDING,
    "STARTED": FineTuningStatus.RUNNING,
    "RUNNING": FineTuningStatus.RUNNING,
    "SUCCESS": FineTuningStatus.SUCCEEDED,
    "SUCCEEDED": FineTuningStatus.SUCCEEDED,
    "FAILED": FineTuningStatus.FAILED,
    "FAILED_VALIDATION": FineTuningStatus.FAILED,
    "CANCELLED": FineTuningStatus.CANCELLED,
    "CANCELLATION_REQUESTED": FineTuningStatus.CANCELLED,
}


class MistralFineTuner:
    """LoRA fine-tuning via Mistral La Plateforme (sovereign EU provider).

    Tenant isolation is enforced by embedding the tenant id in the job suffix and
    filtering list results by that prefix, since the upstream API has no tenant concept.
    """

    def __init__(self, api_key: str) -> None:
        from mistralai import Mistral

        self._client: Mistral = Mistral(api_key=api_key)

    def create_job(self, spec: FineTuningSpec) -> FineTuningJob:
        suffix = _scoped_suffix(spec.tenant_id, spec.hyperparams.suffix)
        payload = "\n".join(
            json.dumps({"messages": [m.model_dump() for m in example.messages]})
            for example in spec.examples
        ).encode("utf-8")
        uploaded = self._client.files.upload(
            file={"file_name": f"{suffix}.jsonl", "content": io.BytesIO(payload)},
            purpose="fine-tune",
        )
        created = self._client.fine_tuning.jobs.create(
            model=spec.base_model,
            training_files=[{"file_id": uploaded.id}],
            hyperparameters={
                "training_steps": spec.hyperparams.epochs,
                "learning_rate": spec.hyperparams.learning_rate,
            },
            suffix=suffix,
            auto_start=True,
        )
        return _to_job(created, spec.tenant_id, spec.hyperparams)

    def get_job(self, job_id: str) -> FineTuningJob:
        retrieved = self._client.fine_tuning.jobs.get(job_id=job_id)
        return _to_job(retrieved, _tenant_of(retrieved), _hyperparams_of(retrieved))

    def list_jobs(self, tenant_id: str) -> list[FineTuningJob]:
        listed = self._client.fine_tuning.jobs.list()
        jobs = getattr(listed, "data", []) or []
        prefix = f"{tenant_id}--"
        return [
            _to_job(job, tenant_id, _hyperparams_of(job))
            for job in jobs
            if str(getattr(job, "suffix", "") or "").startswith(prefix)
        ]

    def cancel_job(self, job_id: str) -> FineTuningJob:
        cancelled = self._client.fine_tuning.jobs.cancel(job_id=job_id)
        return _to_job(cancelled, _tenant_of(cancelled), _hyperparams_of(cancelled))


def _scoped_suffix(tenant_id: str, suffix: str) -> str:
    return f"{tenant_id}--{suffix or 'custom'}"


def _tenant_of(job: object) -> str:
    suffix = str(getattr(job, "suffix", "") or "")
    return suffix.split("--", 1)[0] if "--" in suffix else "default"


def _hyperparams_of(job: object) -> FineTuningHyperParams:
    hyper = getattr(job, "hyperparameters", None)
    suffix = str(getattr(job, "suffix", "") or "")
    short = suffix.split("--", 1)[1] if "--" in suffix else suffix
    return FineTuningHyperParams(
        epochs=int(getattr(hyper, "training_steps", 0) or 0),
        learning_rate=float(getattr(hyper, "learning_rate", 1e-4) or 1e-4),
        suffix=short or "custom",
    )


def _to_job(job: object, tenant_id: str, hyperparams: FineTuningHyperParams) -> FineTuningJob:
    job_id = str(getattr(job, "id", ""))
    if not job_id:
        raise FineTuningJobNotFound(job_id)
    raw_status = str(getattr(job, "status", "QUEUED") or "QUEUED").upper()
    created = getattr(job, "created_at", None)
    created_at = str(created) if created is not None else datetime.now(UTC).isoformat()
    return FineTuningJob(
        id=job_id,
        base_model=str(getattr(job, "model", hyperparams.suffix)),
        status=_STATUS_MAP.get(raw_status, FineTuningStatus.PENDING),
        fine_tuned_model=getattr(job, "fine_tuned_model", None),
        tenant_id=tenant_id,
        created_at=created_at,
        hyperparams=hyperparams,
    )
