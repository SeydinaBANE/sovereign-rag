from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from sovereign_rag.api.schemas import HealthResponse
from sovereign_rag.container import Container, get_container

router = APIRouter(tags=["ops"])


@router.get("/healthz", response_model=HealthResponse)
def healthz(
    container: Annotated[Container, Depends(get_container)],
) -> HealthResponse:
    return HealthResponse(
        status="ok",
        vector_count=container.store.count(),
        audit_chain_valid=container.audit.verify_chain(),
    )
