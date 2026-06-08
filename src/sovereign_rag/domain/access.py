from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Role(StrEnum):
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class Permission(StrEnum):
    INGEST = "ingest"
    QUERY = "query"
    READ_COMPLIANCE = "read_compliance"
    MANAGE = "manage"


_ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.ADMIN: frozenset(Permission),
    Role.EDITOR: frozenset({Permission.INGEST, Permission.QUERY, Permission.READ_COMPLIANCE}),
    Role.VIEWER: frozenset({Permission.QUERY, Permission.READ_COMPLIANCE}),
}


class Principal(BaseModel):
    subject: str
    tenant_id: str
    roles: list[Role] = Field(default_factory=list)


def permissions_for(roles: list[Role]) -> frozenset[Permission]:
    granted: set[Permission] = set()
    for role in roles:
        granted |= _ROLE_PERMISSIONS.get(role, frozenset())
    return frozenset(granted)
