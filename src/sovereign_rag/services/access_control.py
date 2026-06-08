from __future__ import annotations

from sovereign_rag.domain.access import Permission, Principal, permissions_for
from sovereign_rag.domain.exceptions import AuthorizationError


def require(principal: Principal, permission: Permission) -> None:
    if permission not in permissions_for(principal.roles):
        raise AuthorizationError(f"Subject '{principal.subject}' lacks permission '{permission}'.")


def ensure_tenant(principal: Principal, tenant_id: str) -> str:
    if principal.tenant_id != tenant_id:
        raise AuthorizationError(
            f"Subject '{principal.subject}' cannot access tenant '{tenant_id}'."
        )
    return tenant_id
