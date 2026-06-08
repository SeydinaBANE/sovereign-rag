from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

_COST_PER_1K_TOKENS: dict[str, tuple[float, float]] = {
    "mistral-large-latest": (0.002, 0.006),
    "mistral-small-latest": (0.0002, 0.0006),
    "fake-llm": (0.0, 0.0),
}


@dataclass
class Span:
    name: str
    duration_ms: float = 0.0
    attributes: dict[str, float | str] = field(default_factory=dict)


class Tracer:
    """Lightweight tracer; forwards to Langfuse when enabled, else stays in-memory."""

    def __init__(self, enabled: bool = False, client: object | None = None) -> None:
        self._enabled = enabled
        self._client = client
        self.spans: list[Span] = []

    @contextmanager
    def span(self, name: str, **attributes: float | str) -> Iterator[Span]:
        current = Span(name=name, attributes=dict(attributes))
        start = time.perf_counter()
        try:
            yield current
        finally:
            current.duration_ms = (time.perf_counter() - start) * 1000.0
            self.spans.append(current)
            self._export(current)

    def _export(self, span: Span) -> None:
        if not self._enabled or self._client is None:
            return
        trace = getattr(self._client, "trace", None)
        if callable(trace):
            trace(name=span.name, metadata={**span.attributes, "duration_ms": span.duration_ms})


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    input_rate, output_rate = _COST_PER_1K_TOKENS.get(model, (0.0, 0.0))
    return (input_tokens / 1000.0) * input_rate + (output_tokens / 1000.0) * output_rate
