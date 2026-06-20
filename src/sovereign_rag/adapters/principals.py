from __future__ import annotations

import hmac

from sovereign_rag.config import ApiKeyPrincipal
from sovereign_rag.domain.access import Principal


class StaticPrincipalResolver:
    """Resolves API keys to principals from static configuration."""

    def __init__(self, api_keys: list[ApiKeyPrincipal]) -> None:
        self._entries: list[tuple[str, Principal]] = [
            (
                entry.key,
                Principal(
                    subject=entry.subject,
                    tenant_id=entry.tenant_id,
                    roles=entry.roles,
                ),
            )
            for entry in api_keys
        ]

    def resolve(self, api_key: str) -> Principal | None:
        matched: Principal | None = None
        for key, principal in self._entries:
            if hmac.compare_digest(key, api_key):
                matched = principal
        return matched
