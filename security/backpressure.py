from __future__ import annotations

from contextlib import asynccontextmanager
from threading import Lock


class BackpressureError(RuntimeError):
    pass


class QueueDepthGuard:
    """Limits concurrent in-flight calculate_and_persist calls.

    When the number of active requests reaches max_in_flight, new requests
    are rejected immediately (fail-fast) with a BackpressureError rather
    than queuing indefinitely.  This bounds memory usage and prevents
    cascading latency under sustained overload.
    """

    def __init__(self, max_in_flight: int = 200) -> None:
        if max_in_flight <= 0:
            raise ValueError("max_in_flight must be positive")
        self._max = max_in_flight
        self._current = 0
        self._lock = Lock()
        self._rejected_total = 0
        self._peak = 0

    @property
    def current_depth(self) -> int:
        return self._current

    @property
    def rejected_total(self) -> int:
        return self._rejected_total

    @property
    def peak_depth(self) -> int:
        return self._peak

    def acquire(self) -> None:
        with self._lock:
            if self._current >= self._max:
                self._rejected_total += 1
                raise BackpressureError(
                    f"Server overloaded: {self._current}/{self._max} in-flight requests. "
                    "Retry after a short delay."
                )
            self._current += 1
            if self._current > self._peak:
                self._peak = self._current

    def release(self) -> None:
        with self._lock:
            self._current = max(0, self._current - 1)

    @asynccontextmanager
    async def guarded(self):
        """Async context manager that enforces the queue depth limit."""
        self.acquire()
        try:
            yield
        finally:
            self.release()

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "in_flight": self._current,
                "max_in_flight": self._max,
                "peak_in_flight": self._peak,
                "rejected_total": self._rejected_total,
            }
