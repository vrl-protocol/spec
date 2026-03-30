from __future__ import annotations

from decimal import Decimal

from hypothesis import given, settings, strategies as st

from core.engine import calculate_import_landed_cost
from core.verifier import verify_proof
from models.schemas import ImportCalculationRequest
from utils.canonical import canonical_json

hs_codes = st.sampled_from(['8471300100', '8507600000', '6110200000', '6403990000', '8703220000', '9403600000'])
origins = st.sampled_from(['CN', 'US'])
shipping_modes = st.sampled_from(['ocean', 'air', 'truck'])
quantities = st.integers(min_value=1, max_value=10)
amounts = st.decimals(min_value=Decimal('1.00'), max_value=Decimal('5000.00'), places=2, allow_nan=False, allow_infinity=False)


@settings(max_examples=25)
@given(hs_code=hs_codes, country=origins, customs_value=amounts, freight=amounts, insurance=amounts, quantity=quantities, shipping_mode=shipping_modes)
def test_determinism_holds_for_generated_inputs(hs_code: str, country: str, customs_value: Decimal, freight: Decimal, insurance: Decimal, quantity: int, shipping_mode: str) -> None:
    request = ImportCalculationRequest.model_validate({
        'hs_code': hs_code,
        'country_of_origin': country,
        'customs_value': customs_value,
        'freight': freight,
        'insurance': insurance,
        'quantity': quantity,
        'shipping_mode': shipping_mode,
    })
    first = calculate_import_landed_cost(request)
    second = calculate_import_landed_cost(request)
    assert canonical_json(first.model_dump(mode='python')) == canonical_json(second.model_dump(mode='python'))
    verdict = verify_proof(request.model_dump(mode='python'), first.model_dump(mode='python'))
    assert verdict.status == 'VALID'
