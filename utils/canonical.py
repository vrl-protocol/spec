from __future__ import annotations

import unicodedata
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel


def canonicalize(value: Any) -> Any:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="python")
    if is_dataclass(value):
        value = asdict(value)
    if isinstance(value, bool):
        # bool is a subclass of int -- must be checked first.
        return value
    if isinstance(value, float):
        raise TypeError(
            f"Float values are not allowed in canonical payloads: {value!r}"
        )
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, (date, time)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, dict):
        return {str(key): canonicalize(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [canonicalize(item) for item in value]
    if isinstance(value, set):
        return [canonicalize(item) for item in sorted(value, key=lambda item: str(item))]
    return value


def canonical_json(value: Any) -> str:
    import json
    return json.dumps(
        canonicalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
