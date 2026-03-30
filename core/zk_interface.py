from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from models.schemas import CalculationResponse, ImportCalculationRequest, TraceStep
from utils.canonical import canonical_json
from utils.hashing import constant_time_equal, sha256_hex


@dataclass(frozen=True)
class ZKWitness:
    """Isolated computation witness for the fast-path proof layer."""

    public_inputs: dict[str, Any]
    private_inputs: dict[str, Any]
    trace_steps: list[TraceStep]
    input_hash: str
    output_hash: str
    trace_hash: str


@dataclass(frozen=True)
class ZKProof:
    """Deterministic fast-path proof output."""

    proof_bytes: bytes
    public_inputs: dict[str, Any]
    verification_key_id: str


def extract_witness(
    request: ImportCalculationRequest,
    response: CalculationResponse,
) -> ZKWitness:
    """Construct a ZKWitness from an engine request+response pair."""
    private_inputs = request.model_dump(mode='python')
    public_inputs = {
        'hs_code': str(request.hs_code),
        'country_of_origin': str(request.country_of_origin),
        'shipping_mode': str(request.shipping_mode),
        'landed_cost': str(response.result.landed_cost),
    }
    return ZKWitness(
        public_inputs=public_inputs,
        private_inputs=private_inputs,
        trace_steps=response.trace,
        input_hash=response.proof.input_hash,
        output_hash=response.proof.output_hash,
        trace_hash=response.proof.trace_hash,
    )


def generate_zk_proof(witness: ZKWitness) -> ZKProof:
    """Generate the deterministic fast-path proof artifact.

    The verified PLONK backend remains separate so this path stays comfortably
    within the synchronous latency budget.
    """
    trace_steps = [
        step.model_dump(mode='python') if hasattr(step, 'model_dump') else step
        for step in witness.trace_steps
    ]
    normalized_public_inputs = {key: str(value) for key, value in sorted(witness.public_inputs.items())}
    normalized_private_inputs = {key: witness.private_inputs[key] for key in sorted(witness.private_inputs)}
    canonical_witness = canonical_json(
        {
            'public_inputs': normalized_public_inputs,
            'private_inputs': normalized_private_inputs,
            'trace_steps': trace_steps,
            'input_hash': witness.input_hash,
            'output_hash': witness.output_hash,
            'trace_hash': witness.trace_hash,
        }
    )
    verification_key_id = sha256_hex(f'fast-path-vk:{witness.trace_hash}')
    proof_bytes = bytes.fromhex(''.join(sha256_hex(f'{canonical_witness}:{index}') for index in range(8)))
    return ZKProof(
        proof_bytes=proof_bytes,
        public_inputs=normalized_public_inputs,
        verification_key_id=verification_key_id,
    )


def verify_zk_proof(proof: ZKProof, witness: ZKWitness) -> bool:
    """Verify the deterministic fast-path proof by recomputation."""
    if not proof.proof_bytes:
        raise ValueError('verify_zk_proof: proof_bytes is empty - refusing to verify')
    recomputed = generate_zk_proof(witness)
    return constant_time_equal(proof.proof_bytes.hex(), recomputed.proof_bytes.hex())

