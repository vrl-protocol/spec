"""
chain_metrics.py
================
Thread-safe per-chain metrics for the 64-partition audit chain.

Tracks:
  - requests_total[chain_id]     — total write attempts routed to this chain
  - successes_total[chain_id]    — successful persists
  - duplicates_total[chain_id]   — duplicate input_hash rejections
  - errors_total[chain_id]       — unexpected failures (not duplicates)
  - lock_wait_ms_total[chain_id] — cumulative advisory lock wait time (ms)

Hotspot detection:
  chains_above_threshold()  — returns chain_ids where traffic share exceeds
  (2 / AUDIT_CHAIN_PARTITIONS) * hotspot_factor, i.e. more than
  hotspot_factor × the expected average share.
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from threading import Lock
from typing import Generator

from core.audit_chain import AUDIT_CHAIN_PARTITIONS

_EXPECTED_SHARE = 1.0 / AUDIT_CHAIN_PARTITIONS
_DEFAULT_HOTSPOT_FACTOR = 3.0  # flag if chain carries >3× expected traffic share


class ChainMetrics:
    def __init__(self) -> None:
        self._lock = Lock()
        n = AUDIT_CHAIN_PARTITIONS
        self._requests = [0] * n
        self._successes = [0] * n
        self._duplicates = [0] * n
        self._errors = [0] * n
        self._lock_wait_ms = [0.0] * n

    # ------------------------------------------------------------------
    # Recording helpers (called by EvidenceService)
    # ------------------------------------------------------------------

    def record_request(self, chain_id: int) -> None:
        with self._lock:
            self._requests[chain_id] += 1

    def record_success(self, chain_id: int) -> None:
        with self._lock:
            self._successes[chain_id] += 1

    def record_duplicate(self, chain_id: int) -> None:
        with self._lock:
            self._duplicates[chain_id] += 1

    def record_error(self, chain_id: int) -> None:
        with self._lock:
            self._errors[chain_id] += 1

    def record_lock_wait_ms(self, chain_id: int, ms: float) -> None:
        with self._lock:
            self._lock_wait_ms[chain_id] += ms

    @contextmanager
    def timed_lock_wait(self, chain_id: int) -> Generator[None, None, None]:
        """Context manager that measures the time spent waiting for a lock."""
        t0 = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            self.record_lock_wait_ms(chain_id, elapsed_ms)

    # ------------------------------------------------------------------
    # Hotspot detection
    # ------------------------------------------------------------------

    def chains_above_threshold(self, hotspot_factor: float = _DEFAULT_HOTSPOT_FACTOR) -> list[int]:
        """Return chain_ids whose traffic share exceeds hotspot_factor × expected."""
        with self._lock:
            total = sum(self._requests)
        if total == 0:
            return []
        threshold = _EXPECTED_SHARE * hotspot_factor
        with self._lock:
            requests_snapshot = list(self._requests)
        return [
            cid
            for cid, count in enumerate(requests_snapshot)
            if count / total > threshold
        ]

    # ------------------------------------------------------------------
    # Snapshot for observability endpoint
    # ------------------------------------------------------------------

    def snapshot(self) -> dict:
        with self._lock:
            total_requests = sum(self._requests)
            chains = [
                {
                    "chain_id": cid,
                    "requests": self._requests[cid],
                    "successes": self._successes[cid],
                    "duplicates": self._duplicates[cid],
                    "errors": self._errors[cid],
                    "lock_wait_ms_total": round(self._lock_wait_ms[cid], 3),
                    "share_pct": round(
                        100.0 * self._requests[cid] / total_requests, 2
                    ) if total_requests else 0.0,
                }
                for cid in range(AUDIT_CHAIN_PARTITIONS)
            ]
        hotspots = self.chains_above_threshold()
        return {
            "total_requests": total_requests,
            "partitions": AUDIT_CHAIN_PARTITIONS,
            "expected_share_pct": round(100.0 * _EXPECTED_SHARE, 2),
            "hotspot_chains": hotspots,
            "chains": chains,
        }

    def reset(self) -> None:
        """Reset all counters (useful for tests)."""
        with self._lock:
            n = AUDIT_CHAIN_PARTITIONS
            self._requests = [0] * n
            self._successes = [0] * n
            self._duplicates = [0] * n
            self._errors = [0] * n
            self._lock_wait_ms = [0.0] * n


# Module-level singleton — imported by EvidenceService and the metrics endpoint.
chain_metrics = ChainMetrics()
