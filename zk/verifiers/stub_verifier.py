from __future__ import annotations

from backend.trace_adapter import build_trace_packet
from core.zk_interface import ZKWitness, verify_zk_proof, ZKProof
from zk.interfaces import Circuit, Proof, Trace, VerificationResult, Witness, build_verification_artifact
from zk.provers.stub_prover import build_default_circuit_artifact, deterministic_commitments, prove_artifacts, serialize_public_inputs


def verify_artifacts(circuit: Circuit, trace: Trace, witness: Witness, proof: Proof, *, produced_by: str = 'verifier_agent', cycle: int = 1) -> VerificationResult:
    checks: list[str] = []
    valid = True

    zk_witness = ZKWitness(
        public_inputs=witness.public_inputs,
        private_inputs=witness.private_inputs,
        trace_steps=trace.steps,
        input_hash=witness.input_hash,
        output_hash=witness.output_hash,
        trace_hash=witness.trace_hash,
    )
    zk_proof = ZKProof(
        proof_bytes=bytes.fromhex(proof.final_proof),
        public_inputs=witness.public_inputs,
        verification_key_id=proof.metadata.get('verification_key_id', ''),
    )
    if verify_zk_proof(zk_proof, zk_witness):
        checks.append('final_proof_matches_trace_hashes')
    else:
        checks.append('final_proof_mismatch')
        valid = False

    if proof.proof_blob_hex == proof.final_proof:
        checks.append('proof_blob_matches_stub_backend')
    else:
        checks.append('proof_blob_mismatch')
        valid = False

    expected_commitments = deterministic_commitments(circuit, trace, witness)
    if proof.commitments == expected_commitments:
        checks.append('commitments_match_artifact_hashes')
    else:
        checks.append('commitments_mismatch')
        valid = False

    expected_public_inputs = serialize_public_inputs(witness.public_inputs)
    if proof.public_inputs == expected_public_inputs:
        checks.append('public_inputs_match_witness')
    else:
        checks.append('public_inputs_mismatch')
        valid = False

    if proof.circuit_artifact_id == circuit.artifact_id and proof.witness_artifact_id == witness.artifact_id:
        checks.append('proof_bindings_match_dependency_artifacts')
    else:
        checks.append('proof_bindings_mismatch')
        valid = False

    status = 'VALID' if valid else 'INVALID'
    reason = 'all structured proof checks passed' if valid else 'structured proof verification failed'
    return build_verification_artifact(
        subject_artifact_id=proof.artifact_id,
        verifier_backend='sha256-structured-stub-verifier',
        status=status,
        reason=reason,
        checks=checks,
        metadata={
            'proof_system': proof.proof_system,
            'verification_key_id': proof.metadata.get('verification_key_id', ''),
            'trace_artifact_id': trace.artifact_id,
        },
        produced_by=produced_by,
        cycle=cycle,
    )


def verify_request(request_payload: object, expected_proof_hex: str | None = None) -> bool:
    packet = build_trace_packet(request_payload, produced_by='backend_integration', cycle=1)
    circuit = build_default_circuit_artifact(cycle=1)
    proof = prove_artifacts(circuit, packet.trace_artifact, packet.witness_artifact, produced_by='performance_optimization', cycle=1)
    if expected_proof_hex is not None and expected_proof_hex != proof.proof_blob_hex:
        return False
    result = verify_artifacts(circuit, packet.trace_artifact, packet.witness_artifact, proof, produced_by='verifier_agent', cycle=1)
    return result.status == 'VALID'
