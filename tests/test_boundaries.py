from __future__ import annotations

from core.engine import MPF_MAX, MPF_MIN, calculate_import_landed_cost
from models.schemas import ImportCalculationRequest


def _request(customs_value: str) -> ImportCalculationRequest:
    return ImportCalculationRequest.model_validate({
        'hs_code': '8507600000',
        'country_of_origin': 'CN',
        'customs_value': customs_value,
        'freight': '0.00',
        'insurance': '0.00',
        'quantity': 1,
        'shipping_mode': 'ocean',
    })


def test_mpf_floor_applies() -> None:
    response = calculate_import_landed_cost(_request('1.00'))
    assert response.result.mpf_amount == MPF_MIN


def test_mpf_ceiling_applies() -> None:
    response = calculate_import_landed_cost(_request('250000.00'))
    assert response.result.mpf_amount == MPF_MAX
