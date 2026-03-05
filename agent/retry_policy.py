from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class RetryConfig:
    max_attempts: int = 3
    initial_delay_seconds: float = 0.5
    backoff_multiplier: float = 2.0
    max_delay_seconds: float = 4.0


class RetryPolicy:
    """Bounded retry/backoff for transient failures."""

    TRANSIENT_MARKERS = (
        "timed out",
        "timeout",
        "connection reset",
        "temporarily unavailable",
        "service unavailable",
        "too many requests",
        "429",
        "502",
        "503",
        "504",
    )

    def __init__(self, config: RetryConfig | None = None) -> None:
        self.config = config or RetryConfig()

    def should_retry(self, exc: Exception, attempt: int) -> bool:
        if attempt >= self.config.max_attempts:
            return False
        text = str(exc).lower()
        return any(m in text for m in self.TRANSIENT_MARKERS)

    def sleep_for_attempt(self, attempt: int) -> float:
        delay = min(
            self.config.initial_delay_seconds * (self.config.backoff_multiplier ** (attempt - 1)),
            self.config.max_delay_seconds,
        )
        time.sleep(delay)
        return delay
