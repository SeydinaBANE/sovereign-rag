from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from sovereign_rag.api.routers import compliance, fine_tuning, health, ingest, pii, query
from sovereign_rag.config import get_settings
from sovereign_rag.domain.exceptions import (
    AuthenticationError,
    AuthorizationError,
    EmptyCorpusError,
    FineTuningDataError,
    FineTuningDisabledError,
    FineTuningJobNotFound,
    IndexEmptyError,
    InputTooLargeError,
    ResidencyError,
    SovereignRagError,
)

_STATUS = {
    AuthenticationError: 401,
    AuthorizationError: 403,
    ResidencyError: 422,
    InputTooLargeError: 422,
    EmptyCorpusError: 400,
    IndexEmptyError: 409,
    FineTuningDataError: 422,
    FineTuningJobNotFound: 404,
    FineTuningDisabledError: 503,
}

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
}


@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
    get_settings()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Sovereign RAG",
        version="0.1.0",
        description="Sovereign, compliance-by-design RAG accelerator.",
        lifespan=_lifespan,
    )
    app.include_router(health.router)
    app.include_router(ingest.router)
    app.include_router(query.router)
    app.include_router(compliance.router)
    app.include_router(fine_tuning.router)
    app.include_router(pii.router)

    @app.middleware("http")
    async def _security_headers(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        for header, value in _SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        return response

    @app.exception_handler(SovereignRagError)
    async def _handle_domain_error(_: Request, exc: SovereignRagError) -> JSONResponse:
        status = _STATUS.get(type(exc), 400)
        return JSONResponse(status_code=status, content={"detail": str(exc)})

    return app


app = create_app()
