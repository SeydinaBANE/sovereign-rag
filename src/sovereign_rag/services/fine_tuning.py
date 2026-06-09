from __future__ import annotations

from sovereign_rag.compliance.audit import hash_query
from sovereign_rag.config import Settings
from sovereign_rag.domain.access import Permission, Principal
from sovereign_rag.domain.exceptions import FineTuningDataError, FineTuningJobNotFound
from sovereign_rag.domain.models import (
    FineTuningHyperParams,
    FineTuningJob,
    FineTuningSpec,
    TrainingExample,
)
from sovereign_rag.observability.tracing import Tracer
from sovereign_rag.ports.audit import AuditPort
from sovereign_rag.ports.fine_tuning import FineTuningPort
from sovereign_rag.services import access_control


class FineTuningService:
    """Orchestrates tenant-scoped, audited LoRA fine-tuning jobs."""

    def __init__(
        self,
        fine_tuner: FineTuningPort,
        audit: AuditPort,
        settings: Settings,
        tracer: Tracer | None = None,
    ) -> None:
        self._fine_tuner = fine_tuner
        self._audit = audit
        self._settings = settings
        self._tracer = tracer or Tracer()

    def create(
        self,
        examples: list[TrainingExample],
        hyperparams: FineTuningHyperParams,
        principal: Principal,
    ) -> FineTuningJob:
        access_control.require(principal, Permission.MANAGE)
        self._validate(examples)
        spec = FineTuningSpec(
            base_model=self._settings.fine_tuning_base_model,
            examples=examples,
            hyperparams=hyperparams,
            tenant_id=principal.tenant_id,
        )
        with self._tracer.span("fine_tuning.create", base_model=spec.base_model) as span:
            job = self._fine_tuner.create_job(spec)
            span.attributes["job_id"] = job.id
            span.attributes["examples"] = float(len(examples))
        self._audit.record(
            hash_query(f"{spec.base_model}:{hyperparams.suffix}"),
            [spec.base_model],
            self._settings.default_region,
            f"finetune:create:{job.id}",
            principal.tenant_id,
            principal.subject,
        )
        return job

    def get(self, job_id: str, principal: Principal) -> FineTuningJob:
        access_control.require(principal, Permission.MANAGE)
        job = self._fine_tuner.get_job(job_id)
        return self._owned(job, principal)

    def list_jobs(self, principal: Principal) -> list[FineTuningJob]:
        access_control.require(principal, Permission.MANAGE)
        return self._fine_tuner.list_jobs(principal.tenant_id)

    def cancel(self, job_id: str, principal: Principal) -> FineTuningJob:
        access_control.require(principal, Permission.MANAGE)
        self._owned(self._fine_tuner.get_job(job_id), principal)
        cancelled = self._fine_tuner.cancel_job(job_id)
        self._audit.record(
            hash_query(job_id),
            [cancelled.base_model],
            self._settings.default_region,
            f"finetune:cancel:{job_id}",
            principal.tenant_id,
            principal.subject,
        )
        return cancelled

    def _validate(self, examples: list[TrainingExample]) -> None:
        minimum = self._settings.fine_tuning_min_examples
        if len(examples) < minimum:
            raise FineTuningDataError(
                f"At least {minimum} training examples are required, got {len(examples)}."
            )
        if any(not example.messages for example in examples):
            raise FineTuningDataError("Every training example must contain at least one message.")

    @staticmethod
    def _owned(job: FineTuningJob, principal: Principal) -> FineTuningJob:
        if job.tenant_id != principal.tenant_id:
            raise FineTuningJobNotFound(job.id)
        return job
