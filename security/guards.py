from __future__ import annotations

import re
from typing import Any

from utils.canonical import canonical_json

MAX_REQUEST_BYTES = 8192
MAX_STRING_BYTES = 256
MAX_COLLECTION_ITEMS = 256

INJECTION_PATTERNS = (
    re.compile(r'(--|/\*|\*/|;)', re.IGNORECASE),
    re.compile(r'\b(select|insert|update|delete|drop|union|alter|create|truncate|xp_)\b', re.IGNORECASE),
    re.compile(r'<\s*script\b', re.IGNORECASE),
)


class SecurityViolation(ValueError):
    pass


def _walk(value: Any) -> None:
    if isinstance(value, dict):
        if len(value) > MAX_COLLECTION_ITEMS:
            raise SecurityViolation('Payload contains too many keys')
        for key, item in value.items():
            _walk(key)
            _walk(item)
        return
    if isinstance(value, (list, tuple, set)):
        if len(value) > MAX_COLLECTION_ITEMS:
            raise SecurityViolation('Payload contains too many items')
        for item in value:
            _walk(item)
        return
    if isinstance(value, str):
        if len(value.encode('utf-8')) > MAX_STRING_BYTES:
            raise SecurityViolation('String value exceeds size limit')
        if any(pattern.search(value) for pattern in INJECTION_PATTERNS):
            raise SecurityViolation('Potential injection pattern detected')
        return
    if isinstance(value, float):
        raise SecurityViolation('Floating point values are not allowed')
    if isinstance(value, (int, bool, type(None))):
        return
    from decimal import Decimal

    if isinstance(value, Decimal):
        return
    raise SecurityViolation(f'Unsupported payload type: {type(value).__name__}')


def enforce_payload_guards(payload: Any) -> None:
    raw = canonical_json(payload)
    if len(raw.encode('utf-8')) > MAX_REQUEST_BYTES:
        raise SecurityViolation('Payload exceeds maximum request size')
    _walk(payload)
