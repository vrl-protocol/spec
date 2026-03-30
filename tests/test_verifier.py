from __future__ import annotations

from core.engine import calculate_import_landed_cost
from core.sample import REFERENCE_REQUEST
from core.verifier import verify_proof
from models.schemas import ImportCalculationRequest


def test_verifier_accepts_valid_response() -> None:
    request = ImportCalculationRequest.model_validate(REFERENCE_REQUEST)
    response = calculate_import_landed_cost(request)
    verdict = verify_proof(request.model_dump(mode='python'), response.model_dump(mode='python'))
    assert verdict.status == 'VALID'


def test_verifier_rejects_tampered_response() -> None:
    request = ImportCalculationRequest.model_validate(REFERENCE_REQUEST)
    response = calculate_import_landed_cost(request)
    tampered = response.model_copy(deep=True)
    tampered.result.landed_cost = tampered.result.landed_cost + 1
    verdict = verify_proof(request.model_dump(mode='python'), tampered.model_dump(mode='python'))
    assert verdict.status == 'INVALID'
