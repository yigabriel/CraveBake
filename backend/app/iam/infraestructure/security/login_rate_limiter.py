"""
In-memory limiter for failed login attempts (brute-force protection).

Counts failures per key inside a sliding window; once a key reaches the
limit, further attempts are rejected until the oldest failure leaves the
window. A successful login clears the key.

State lives in the process, so each worker keeps its own counters and they
reset on restart. Swap for a Redis-backed implementation when the API runs
with several workers or instances.
"""
from __future__ import annotations

import math
import time
from collections import deque
from collections.abc import Callable

from app.shared.exceptions.domain_exceptions import TooManyRequestsError


class LoginRateLimiter:

    def __init__(
        self,
        max_failures: int,
        window_seconds: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max_failures = max_failures
        self._window_seconds = window_seconds
        self._clock = clock
        self._failures: dict[str, deque[float]] = {}

    def ensure_allowed(self, key: str) -> None:
        failures = self._recent_failures(key)
        if len(failures) >= self._max_failures:
            retry_after = math.ceil(failures[0] + self._window_seconds - self._clock())
            raise TooManyRequestsError(
                "Too many failed login attempts. Try again later.",
                retry_after_seconds=max(retry_after, 1),
            )

    def register_failure(self, key: str) -> None:
        self._recent_failures(key).append(self._clock())

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)

    def _recent_failures(self, key: str) -> deque[float]:
        failures = self._failures.setdefault(key, deque())
        cutoff = self._clock() - self._window_seconds
        while failures and failures[0] <= cutoff:
            failures.popleft()
        return failures
