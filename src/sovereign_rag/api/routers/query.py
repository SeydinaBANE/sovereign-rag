from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from sovereign_rag.api.limits import enforce_query_limits
from sovereign_rag.api.schemas import QueryRequest
from sovereign_rag.api.security import CurrentPrincipal
from sovereign_rag.container import Container, get_container
from sovereign_rag.domain.models import Answer, Query

router = APIRouter(tags=["rag"])


@router.post("/query", response_model=Answer)
def query(
    request: QueryRequest,
    principal: CurrentPrincipal,
    container: Annotated[Container, Depends(get_container)],
) -> Answer:
    enforce_query_limits(request, container.settings)
    return container.rag.answer(
        Query(text=request.text, top_k=request.top_k, regions=request.regions),
        principal,
    )
