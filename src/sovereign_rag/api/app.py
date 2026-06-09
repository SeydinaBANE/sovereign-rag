from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from sovereign_rag.api.routers import compliance, fine_tuning, health, ingest, query
from sovereign_rag.domain.exceptions import (
    AuthenticationError,
    AuthorizationError,
    EmptyCorpusError,
    FineTuningDataError,
    FineTuningDisabledError,
    FineTuningJobNotFound,
    IndexEmptyError,
    ResidencyError,
    SovereignRagError,
)

_STATUS = {
    AuthenticationError: 401,
    AuthorizationError: 403,
    ResidencyError: 422,
    EmptyCorpusError: 400,
    IndexEmptyError: 409,
    FineTuningDataError: 422,
    FineTuningJobNotFound: 404,
    FineTuningDisabledError: 503,
}


def create_app() -> FastAPI:
    app = FastAPI(
        title="Sovereign RAG",
        version="0.1.0",
        description="Sovereign, compliance-by-design RAG accelerator.",
    )
    app.include_router(health.router)
    app.include_router(ingest.router)
    app.include_router(query.router)
    app.include_router(compliance.router)
    app.include_router(fine_tuning.router)

    @app.exception_handler(SovereignRagError)
    async def _handle_domain_error(_: Request, exc: SovereignRagError) -> JSONResponse:
        status = _STATUS.get(type(exc), 400)
        return JSONResponse(status_code=status, content={"detail": str(exc)})

    return app


app = create_app()
