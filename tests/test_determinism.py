from __future__ import annotations

from core.engine import calculate_import_landed_cost
from core.sample import REFERENCE_REQUEST
from models.schemas import ImportCalculationRequest
from utils.canonical import canonical_json


def test_same_input_produces_identical_output_and_proof() -> None:
    request = ImportCalculationRequest.model_validate(REFERENCE_REQUEST)
    first = calculate_import_landed_cost(request)
    second = calculate_import_landed_cost(request)

    assert canonical_json(first.model_dump(mode='python')) == canonical_json(second.model_dump(mode='python'))
    assert first.integrity.model_dump(mode='python') == second.integrity.model_dump(mode='python')
