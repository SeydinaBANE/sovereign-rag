from __future__ import annotations

from typing import Protocol, runtime_checkable

from sovereign_rag.domain.models import FineTuningJob, FineTuningSpec


@runtime_checkable
class FineTuningPort(Protocol):
    def create_job(self, spec: FineTuningSpec) -> FineTuningJob: ...

    def get_job(self, job_id: str) -> FineTuningJob: ...

    def list_jobs(self, tenant_id: str) -> list[FineTuningJob]: ...

    def cancel_job(self, job_id: str) -> FineTuningJob: ...
