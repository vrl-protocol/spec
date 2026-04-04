from __future__ import annotations

from models.schemas import IntegrityArtifact
from utils.canonical import canonical_json
from utils.hashing import sha256_hex


def build_integrity_artifact(request_payload: object, result_payload: object, trace_payload: object) -> IntegrityArtifact:
    input_hash = sha256_hex(canonical_json(request_payload))
    output_hash = sha256_hex(canonical_json(result_payload))
    trace_hash = sha256_hex(canonical_json(trace_payload))
    integrity_hash = sha256_hex(input_hash + output_hash + trace_hash)
    return IntegrityArtifact(
        input_hash=input_hash,
        output_hash=output_hash,
        trace_hash=trace_hash,
        integrity_hash=integrity_hash,
    )
