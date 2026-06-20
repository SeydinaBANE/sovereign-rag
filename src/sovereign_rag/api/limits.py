from __future__ import annotations

from sovereign_rag.api.schemas import IngestRequest, QueryRequest
from sovereign_rag.config import Settings
from sovereign_rag.domain.exceptions import InputTooLargeError


def enforce_query_limits(request: QueryRequest, settings: Settings) -> None:
    if len(request.text) > settings.max_query_chars:
        raise InputTooLargeError(f"Query exceeds {settings.max_query_chars} characters.")
    if request.top_k is not None and not 1 <= request.top_k <= settings.max_top_k:
        raise InputTooLargeError(f"top_k must be between 1 and {settings.max_top_k}.")


def enforce_ingest_limits(request: IngestRequest, settings: Settings) -> None:
    if len(request.documents) > settings.max_documents_per_request:
        raise InputTooLargeError(f"Request exceeds {settings.max_documents_per_request} documents.")
    for document in request.documents:
        if len(document.text) > settings.max_document_chars:
            raise InputTooLargeError(
                f"Document '{document.id}' exceeds {settings.max_document_chars} characters."
            )
