from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from sovereign_rag.api.schemas import DetokenizeResponse, PIITextRequest
from sovereign_rag.api.security import CurrentPrincipal
from sovereign_rag.compliance.audit import hash_query
from sovereign_rag.container import Container, get_container
from sovereign_rag.domain.access import Permission
from sovereign_rag.domain.models import TokenizationResult
from sovereign_rag.services import access_control

router = APIRouter(prefix="/pii", tags=["pii"])


@router.post("/tokenize", response_model=TokenizationResult)
def tokenize(
    request: PIITextRequest,
    principal: CurrentPrincipal,
    container: Annotated[Container, Depends(get_container)],
) -> TokenizationResult:
    access_control.require(principal, Permission.INGEST)
    result = container.vault.tokenize(request.text, principal.tenant_id)
    container.audit.record(
        hash_query(request.text),
        [],
        container.settings.default_region,
        f"pii:tokenize:{len(result.tokens)}",
        principal.tenant_id,
        principal.subject,
    )
    return result


@router.post("/detokenize", response_model=DetokenizeResponse)
def detokenize(
    request: PIITextRequest,
    principal: CurrentPrincipal,
    container: Annotated[Container, Depends(get_container)],
) -> DetokenizeResponse:
    access_control.require(principal, Permission.MANAGE)
    restored = container.vault.detokenize(request.text, principal.tenant_id)
    container.audit.record(
        hash_query(request.text),
        [],
        container.settings.default_region,
        "pii:detokenize",
        principal.tenant_id,
        principal.subject,
    )
    return DetokenizeResponse(text=restored)
