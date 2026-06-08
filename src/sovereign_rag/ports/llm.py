from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class LLMResponse(BaseModel):
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""


@runtime_checkable
class LLMPort(Protocol):
    def complete(self, system: str, prompt: str) -> LLMResponse: ...
