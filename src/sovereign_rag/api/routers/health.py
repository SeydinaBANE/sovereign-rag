from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from sovereign_rag.api.schemas import HealthResponse, ReadinessResponse
from sovereign_rag.container import Container, get_container

router = APIRouter(tags=["ops"])


@router.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/readyz", response_model=ReadinessResponse)
def readyz(
    container: Annotated[Container, Depends(get_container)],
) -> ReadinessResponse:
    return ReadinessResponse(status="ready", vector_count=container.store.count())
