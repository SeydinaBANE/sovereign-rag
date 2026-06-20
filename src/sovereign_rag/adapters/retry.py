from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    """Bounded exponential-backoff retry for idempotent outbound calls."""

    attempts: int = 1
    base_delay: float = 0.2


def retry_call(operation: Callable[[], T], policy: RetryPolicy) -> T:
    attempts = max(policy.attempts, 1)
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except Exception:
            if attempt >= attempts:
                raise
            time.sleep(policy.base_delay * (2 ** (attempt - 1)))
    raise RuntimeError("unreachable")
