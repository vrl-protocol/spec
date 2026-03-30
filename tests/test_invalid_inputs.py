from __future__ import annotations

import pytest

from models.schemas import ImportCalculationRequest
from security.guards import SecurityViolation, enforce_payload_guards


def test_rejects_invalid_hs_code_format() -> None:
    with pytest.raises(Exception):
        ImportCalculationRequest.model_validate({
            'hs_code': 'ABC',
            'country_of_origin': 'CN',
            'customs_value': '10.00',
            'freight': '0.00',
            'insurance': '0.00',
            'quantity': 1,
            'shipping_mode': 'ocean',
        })


def test_rejects_injection_patterns() -> None:
    with pytest.raises(SecurityViolation):
        enforce_payload_guards({'hs_code': '8507600000', 'note': '1; drop table calculations'})


def test_rejects_oversized_payload() -> None:
    with pytest.raises(SecurityViolation):
        enforce_payload_guards({'value': 'x' * 1000})
