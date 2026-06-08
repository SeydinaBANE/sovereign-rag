from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from sovereign_rag.api.schemas import CardRequest
from sovereign_rag.compliance.model_card import build_card
from sovereign_rag.container import Container, get_container
from sovereign_rag.domain.models import ModelCard

router = APIRouter(prefix="/compliance", tags=["compliance"])


@router.get("/card", response_model=ModelCard)
def card(
    container: Annotated[Container, Depends(get_container)],
    system_name: str = "sovereign-rag-demo",
    purpose: str = "Enterprise document question answering assistant (RAG)",
) -> ModelCard:
    settings = container.settings
    return build_card(
        system_name=system_name,
        purpose=purpose,
        llm_model=settings.llm_model,
        embedding_model=settings.embedding_model,
        data_sources=[],
        regions=settings.allowed_regions,
    )


@router.post("/card", response_model=ModelCard)
def card_for(
    request: CardRequest,
    container: Annotated[Container, Depends(get_container)],
) -> ModelCard:
    settings = container.settings
    return build_card(
        system_name=request.system_name,
        purpose=request.purpose,
        llm_model=settings.llm_model,
        embedding_model=settings.embedding_model,
        data_sources=[],
        regions=settings.allowed_regions,
    )
