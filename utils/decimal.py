from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, getcontext
from typing import Any

getcontext().prec = 28
MONEY_QUANTUM = Decimal('0.01')
RATE_QUANTUM = Decimal('0.000001')


def to_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        raise TypeError('Boolean values are not valid decimals')
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, str):
        value = value.strip()
        if not value:
            raise ValueError('Empty string is not a valid decimal')
        try:
            return Decimal(value)
        except InvalidOperation as exc:
            raise ValueError(f'Invalid decimal value: {value!r}') from exc
    raise TypeError(f'Unsupported decimal type: {type(value).__name__}')


def money(value: Any) -> Decimal:
    return to_decimal(value).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def rate(value: Any) -> Decimal:
    return to_decimal(value).quantize(RATE_QUANTUM, rounding=ROUND_HALF_UP)


def clamp_money(value: Any, minimum: Any | None = None, maximum: Any | None = None) -> Decimal:
    amount = money(value)
    if minimum is not None:
        minimum_amount = money(minimum)
        if amount < minimum_amount:
            return minimum_amount
    if maximum is not None:
        maximum_amount = money(maximum)
        if amount > maximum_amount:
            return maximum_amount
    return amount


def format_decimal(value: Any) -> str:
    decimal_value = to_decimal(value)
    normalized = decimal_value.normalize()
    if normalized == normalized.to_integral():
        return format(normalized.quantize(Decimal('1')), 'f')
    return format(normalized, 'f')
