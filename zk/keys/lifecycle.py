"""Key lifecycle event log — append-only, hash-linked.

Every time keys are generated or rotated, an event is written to
logs/key_lifecycle.jsonl.  Each record chains its prev_hash so the log
can be verified for tampering in the same way as the main audit chain.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from utils.canonical import canonical_json
from utils.hashing import sha256_hex

_LIFECYCLE_LOG = Path(__file__).resolve().parents[2] / 'logs' / 'key_lifecycle.jsonl'
_ZERO_HASH = '0' * 64
_lock = threading.Lock()
_prev_hash: str = _ZERO_HASH


def _append_event(event_type: str, payload: dict[str, Any]) -> str:
    global _prev_hash
    _LIFECYCLE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        record: dict[str, Any] = {
            'event_type': event_type,
            'recorded_at': datetime.now(timezone.utc).isoformat(),
            'payload': payload,
            'prev_hash': _prev_hash,
        }
        current_hash = sha256_hex(_prev_hash + canonical_json({
            'event_type': record['event_type'],
            'recorded_at': record['recorded_at'],
            'payload': record['payload'],
        }))
        record['current_hash'] = current_hash
        _prev_hash = current_hash
        with _LIFECYCLE_LOG.open('a', encoding='utf-8', newline='\n') as fh:
            fh.write(canonical_json(record) + '\n')
    return current_hash


def log_key_generation(
    *,
    circuit_hash: str,
    proving_key_id: str,
    verification_key_id: str,
    params_k: int,
    backend_version: str,
) -> str:
    """Record a key-generation event.  Returns the current_hash of the event."""
    return _append_event('key_generation', {
        'circuit_hash': circuit_hash,
        'proving_key_id': proving_key_id,
        'verification_key_id': verification_key_id,
        'params_k': params_k,
        'backend_version': backend_version,
    })


def log_key_rotation(
    *,
    old_circuit_hash: str,
    new_circuit_hash: str,
    proving_key_id: str,
    verification_key_id: str,
    reason: str,
) -> str:
    """Record a key-rotation event.  Returns the current_hash of the event."""
    return _append_event('key_rotation', {
        'old_circuit_hash': old_circuit_hash,
        'new_circuit_hash': new_circuit_hash,
        'proving_key_id': proving_key_id,
        'verification_key_id': verification_key_id,
        'reason': reason,
    })
