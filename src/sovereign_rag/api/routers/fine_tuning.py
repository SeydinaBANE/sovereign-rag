from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from sovereign_rag.api.schemas import FineTuningRequest
from sovereign_rag.api.security import CurrentPrincipal
from sovereign_rag.container import Container, get_container
from sovereign_rag.domain.exceptions import FineTuningDisabledError
from sovereign_rag.domain.models import (
    ChatMessage,
    FineTuningHyperParams,
    FineTuningJob,
    TrainingExample,
)
from sovereign_rag.services.fine_tuning import FineTuningService

router = APIRouter(prefix="/fine-tuning", tags=["fine-tuning"])


def _service(container: Container) -> FineTuningService:
    if container.fine_tuning is None:
        raise FineTuningDisabledError()
    return container.fine_tuning


@router.post("/jobs", response_model=FineTuningJob)
def create_job(
    request: FineTuningRequest,
    principal: CurrentPrincipal,
    container: Annotated[Container, Depends(get_container)],
) -> FineTuningJob:
    settings = container.settings
    examples = [
        TrainingExample(
            messages=[ChatMessage(role=m.role, content=m.content) for m in example.messages]
        )
        for example in request.examples
    ]
    hyperparams = FineTuningHyperParams(
        epochs=request.epochs or settings.fine_tuning_epochs,
        learning_rate=request.learning_rate or settings.fine_tuning_learning_rate,
        suffix=request.suffix or settings.fine_tuning_suffix,
    )
    return _service(container).create(examples, hyperparams, principal)


@router.get("/jobs", response_model=list[FineTuningJob])
def list_jobs(
    principal: CurrentPrincipal,
    container: Annotated[Container, Depends(get_container)],
) -> list[FineTuningJob]:
    return _service(container).list_jobs(principal)


@router.get("/jobs/{job_id}", response_model=FineTuningJob)
def get_job(
    job_id: str,
    principal: CurrentPrincipal,
    container: Annotated[Container, Depends(get_container)],
) -> FineTuningJob:
    return _service(container).get(job_id, principal)


@router.post("/jobs/{job_id}/cancel", response_model=FineTuningJob)
def cancel_job(
    job_id: str,
    principal: CurrentPrincipal,
    container: Annotated[Container, Depends(get_container)],
) -> FineTuningJob:
    return _service(container).cancel(job_id, principal)
