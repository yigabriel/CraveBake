"""
In-memory sliding-window limiter: at most N requests per key in a time window.

Every suggestion is billable (per character), so one signed-in user cannot run
the quota out. State lives in the process: each worker counts on its own and a
restart resets it. Swap for a shared store if the API runs on several instances.
"""
from __future__ import annotations

import math
import time
from collections import deque
from collections.abc import Callable

from app.shared.exceptions.domain_exceptions import TooManyRequestsError


class RequestRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int, clock: Callable[[], float] = time.monotonic) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}

    def hit(self, key: str) -> None:
        """Counts a request; raises `TooManyRequestsError` when the key is over the limit."""
        now = self._clock()
        hits = self._hits.setdefault(key, deque())
        while hits and hits[0] <= now - self._window_seconds:
            hits.popleft()
        if len(hits) >= self._max_requests:
            raise TooManyRequestsError(
                "Too many translation requests. Try again in a moment.",
                retry_after_seconds=max(math.ceil(hits[0] + self._window_seconds - now), 1),
            )
        hits.append(now)
