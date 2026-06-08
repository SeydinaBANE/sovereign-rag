from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from sovereign_rag.container import Container, get_container
from sovereign_rag.domain.access import Principal, Role
from sovereign_rag.domain.exceptions import AuthenticationError


def _extract_api_key(request: Request) -> str | None:
    header = request.headers.get("x-api-key")
    if header:
        return header
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def get_principal(
    request: Request,
    container: Annotated[Container, Depends(get_container)],
) -> Principal:
    settings = container.settings
    if not settings.auth_enabled:
        return Principal(
            subject="local",
            tenant_id=settings.default_tenant,
            roles=[Role.ADMIN],
        )
    api_key = _extract_api_key(request)
    if not api_key:
        raise AuthenticationError("Missing API key.")
    principal = container.principals.resolve(api_key)
    if principal is None:
        raise AuthenticationError("Invalid API key.")
    return principal


CurrentPrincipal = Annotated[Principal, Depends(get_principal)]
