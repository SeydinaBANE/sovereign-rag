from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from sovereign_rag.api.schemas import IngestRequest, IngestResponse
from sovereign_rag.api.security import CurrentPrincipal
from sovereign_rag.container import Container, get_container
from sovereign_rag.domain.access import Permission
from sovereign_rag.domain.models import Document
from sovereign_rag.services import access_control

router = APIRouter(tags=["rag"])


@router.post("/ingest", response_model=IngestResponse)
def ingest(
    request: IngestRequest,
    principal: CurrentPrincipal,
    container: Annotated[Container, Depends(get_container)],
) -> IngestResponse:
    access_control.require(principal, Permission.INGEST)
    default_region = container.settings.default_region
    documents = [
        Document(
            id=item.id,
            text=item.text,
            source=item.source,
            region=item.region or default_region,
            metadata=item.metadata,
        )
        for item in request.documents
    ]
    indexed = container.ingestion.ingest(documents, principal.tenant_id)
    return IngestResponse(chunks_indexed=indexed, total_chunks=container.store.count())
