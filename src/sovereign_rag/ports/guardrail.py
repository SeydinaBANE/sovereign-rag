from __future__ import annotations

from typing import Protocol, runtime_checkable

from sovereign_rag.domain.models import GuardrailResult


@runtime_checkable
class GuardrailPort(Protocol):
    def scan_input(self, text: str) -> GuardrailResult: ...

    def scan_output(self, text: str) -> GuardrailResult: ...
