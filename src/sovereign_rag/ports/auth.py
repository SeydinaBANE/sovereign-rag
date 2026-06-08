from __future__ import annotations

from typing import Protocol, runtime_checkable

from sovereign_rag.domain.access import Principal


@runtime_checkable
class PrincipalResolverPort(Protocol):
    def resolve(self, api_key: str) -> Principal | None: ...
