from __future__ import annotations

import hashlib
import hmac
from typing import Union

BytesLike = Union[str, bytes, bytearray, memoryview]


def _to_bytes(value: BytesLike) -> bytes:
    if isinstance(value, str):
        return value.encode('utf-8')
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, memoryview):
        return value.tobytes()
    raise TypeError(f'Unsupported byte value: {type(value).__name__}')


def sha256_hex(value: BytesLike) -> str:
    return hashlib.sha256(_to_bytes(value)).hexdigest()


def constant_time_equal(left: str, right: str) -> bool:
    return hmac.compare_digest(left, right)
