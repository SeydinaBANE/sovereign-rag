from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from sovereign_rag.api.schemas import AuditVerification, CardRequest
from sovereign_rag.api.security import CurrentPrincipal
from sovereign_rag.compliance.model_card import build_card
from sovereign_rag.container import Container, get_container
from sovereign_rag.domain.access import Permission
from sovereign_rag.domain.models import ModelCard
from sovereign_rag.services import access_control

router = APIRouter(prefix="/compliance", tags=["compliance"])


@router.get("/card", response_model=ModelCard)
def card(
    principal: CurrentPrincipal,
    container: Annotated[Container, Depends(get_container)],
    system_name: str = "sovereign-rag-demo",
    purpose: str = "Enterprise document question answering assistant (RAG)",
) -> ModelCard:
    access_control.require(principal, Permission.READ_COMPLIANCE)
    settings = container.settings
    return build_card(
        system_name=system_name,
        purpose=purpose,
        llm_model=settings.llm_model,
        embedding_model=settings.embedding_model,
        data_sources=[],
        regions=settings.allowed_regions,
    )


@router.get("/audit/verify", response_model=AuditVerification)
def audit_verify(
    principal: CurrentPrincipal,
    container: Annotated[Container, Depends(get_container)],
) -> AuditVerification:
    access_control.require(principal, Permission.READ_COMPLIANCE)
    return AuditVerification(valid=container.audit.verify_chain())


@router.post("/card", response_model=ModelCard)
def card_for(
    request: CardRequest,
    principal: CurrentPrincipal,
    container: Annotated[Container, Depends(get_container)],
) -> ModelCard:
    access_control.require(principal, Permission.READ_COMPLIANCE)
    settings = container.settings
    return build_card(
        system_name=request.system_name,
        purpose=request.purpose,
        llm_model=settings.llm_model,
        embedding_model=settings.embedding_model,
        data_sources=[],
        regions=settings.allowed_regions,
    )
