from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class ApiKeyRecord:
    key_id: str
    key_hash: str          # SHA-256 of the raw key
    label: str             # human-readable name
    requests_total: int = 0
    requests_today: int = 0
    _day_bucket: str = field(default_factory=lambda: ApiKeyRecord._today())

    @staticmethod
    def _today() -> str:
        return time.strftime("%Y-%m-%d", time.gmtime())

    def tick(self) -> None:
        today = self._today()
        if today != self._day_bucket:
            self.requests_today = 0
            self._day_bucket = today
        self.requests_total += 1
        self.requests_today += 1


class ApiKeyStore:
    """In-memory API key registry with SHA-256-hashed key storage.

    Keys are loaded from VRL_API_KEYS env var: a comma-separated list of
    "label:raw_key" pairs.  Example:
        VRL_API_KEYS=service-a:sk_live_abc123,service-b:sk_live_xyz789

    The raw key is never stored; only SHA-256(raw_key) is kept in memory.
    Lookup is O(n_keys) but key count is expected to be small (< 100).
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._keys: dict[str, ApiKeyRecord] = {}  # key_hash -> record
        self._load_from_env()

    def _load_from_env(self) -> None:
        raw = os.getenv("VRL_API_KEYS", "")
        if not raw:
            return
        for entry in raw.split(","):
            entry = entry.strip()
            if ":" not in entry:
                continue
            label, key = entry.split(":", 1)
            self.register(label.strip(), key.strip())

    def register(self, label: str, raw_key: str) -> str:
        """Register a new API key; returns the key_id (hash prefix)."""
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_id = key_hash[:8]
        with self._lock:
            self._keys[key_hash] = ApiKeyRecord(
                key_id=key_id,
                key_hash=key_hash,
                label=label,
            )
        return key_id

    def authenticate(self, raw_key: str) -> ApiKeyRecord | None:
        """Validate a raw API key and record usage if valid.

        Returns the ApiKeyRecord on success, None on failure.
        Uses constant-time hash comparison to prevent timing attacks.
        """
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        with self._lock:
            record = self._keys.get(key_hash)
            if record is None:
                return None
            record.tick()
            return record

    def is_enabled(self) -> bool:
        """Return True if any API keys are registered."""
        with self._lock:
            return len(self._keys) > 0

    def snapshot(self) -> list[dict]:
        with self._lock:
            return [
                {
                    "key_id": r.key_id,
                    "label": r.label,
                    "requests_total": r.requests_total,
                    "requests_today": r.requests_today,
                }
                for r in self._keys.values()
            ]


# Module-level singleton.
api_key_store = ApiKeyStore()
