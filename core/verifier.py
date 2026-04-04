from __future__ import annotations

from pydantic import ValidationError

from core.engine import calculate_import_landed_cost
from models.schemas import CalculationResponse, ImportCalculationRequest, VerificationResult
from utils.canonical import canonical_json
from utils.hashing import constant_time_equal, sha256_hex


def verify_proof(request_payload: object, response_payload: object) -> VerificationResult:
    try:
        try:
            request = ImportCalculationRequest.model_validate(request_payload)
        except ValidationError as exc:
            return VerificationResult(
                status="INVALID",
                reason=f"Invalid verification request payload: {exc}",
                recomputed_input_hash="",
                recomputed_output_hash="",
                recomputed_trace_hash="",
                recomputed_integrity_hash="",
            )
        recomputed = calculate_import_landed_cost(request)
        try:
            response = CalculationResponse.model_validate(response_payload)
        except ValidationError as exc:
            return VerificationResult(
                status="INVALID",
                reason=f"Invalid calculation response payload: {exc}",
                recomputed_input_hash=recomputed.integrity.input_hash,
                recomputed_output_hash=recomputed.integrity.output_hash,
                recomputed_trace_hash=recomputed.integrity.trace_hash,
                recomputed_integrity_hash=recomputed.integrity.integrity_hash,
            )

        recomputed_input_hash = sha256_hex(canonical_json(request.model_dump(mode="python")))
        recomputed_output_hash = sha256_hex(canonical_json(recomputed.result.model_dump(mode="python")))
        recomputed_trace_hash = sha256_hex(canonical_json([step.model_dump(mode="python") for step in recomputed.trace]))
        recomputed_integrity_hash = sha256_hex(recomputed_input_hash + recomputed_output_hash + recomputed_trace_hash)

        checks = [
            constant_time_equal(response.integrity.input_hash, recomputed_input_hash),
            constant_time_equal(response.integrity.output_hash, recomputed_output_hash),
            constant_time_equal(response.integrity.trace_hash, recomputed_trace_hash),
            constant_time_equal(canonical_json(response.result.model_dump(mode="python")), canonical_json(recomputed.result.model_dump(mode="python"))),
            constant_time_equal(canonical_json([step.model_dump(mode="python") for step in response.trace]), canonical_json([step.model_dump(mode="python") for step in recomputed.trace])),
        ]

        if all(checks):
            return VerificationResult(
                status="VALID",
                reason="Proof recomputed successfully",
                recomputed_input_hash=recomputed_input_hash,
                recomputed_output_hash=recomputed_output_hash,
                recomputed_trace_hash=recomputed_trace_hash,
                recomputed_integrity_hash=recomputed_integrity_hash,
            )

        return VerificationResult(
            status="INVALID",
            reason="Recomputed proof or payload mismatch detected",
            recomputed_input_hash=recomputed_input_hash,
            recomputed_output_hash=recomputed_output_hash,
            recomputed_trace_hash=recomputed_trace_hash,
            recomputed_integrity_hash=recomputed_integrity_hash,
        )
    except Exception as exc:
        return VerificationResult(
            status="INVALID",
            reason=f"Verification failed safely: {exc}",
            recomputed_input_hash="",
            recomputed_output_hash="",
            recomputed_trace_hash="",
            recomputed_integrity_hash="",
        )
