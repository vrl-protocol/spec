from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from time import time


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    remaining: int
    reset_after_seconds: int


class RateLimiter:
    def __init__(self, limit: int = 60, window_seconds: int = 60) -> None:
        if limit <= 0:
            raise ValueError('limit must be positive')
        if window_seconds <= 0:
            raise ValueError('window_seconds must be positive')
        self._limit = limit
        self._window_seconds = window_seconds
        self._hits = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> RateLimitResult:
        now = time()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= self._window_seconds:
                hits.popleft()
            if len(hits) >= self._limit:
                reset_after = int(self._window_seconds - (now - hits[0])) if hits else self._window_seconds
                return RateLimitResult(False, 0, max(reset_after, 0))
            hits.append(now)
            remaining = max(self._limit - len(hits), 0)
            return RateLimitResult(True, remaining, self._window_seconds)
