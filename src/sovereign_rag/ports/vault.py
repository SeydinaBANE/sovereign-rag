from __future__ import annotations

from typing import Protocol, runtime_checkable

from sovereign_rag.domain.models import TokenizationResult


@runtime_checkable
class PIIVaultPort(Protocol):
    def tokenize(self, text: str, tenant_id: str) -> TokenizationResult: ...

    def detokenize(self, text: str, tenant_id: str) -> str: ...

    def resolve(self, token: str, tenant_id: str) -> str | None: ...
