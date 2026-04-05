from __future__ import annotations

import time
from statistics import mean

from backend.trace_adapter import build_trace_packet
from core.sample import REFERENCE_REQUEST
from core.zk_interface import ZKWitness, generate_zk_proof
from utils.canonical import canonical_json
from utils.hashing import sha256_hex
from zk.circuits.import_landed_cost_stub import build_circuit_blueprint
from zk.interfaces import Circuit, Proof, Trace, Witness, build_circuit_artifact, build_proof_artifact


def build_default_circuit_artifact(*, produced_by: str = 'circuit_engineer', cycle: int = 1) -> Circuit:
    blueprint = build_circuit_blueprint()
    return build_circuit_artifact(
        name=blueprint.name,
        description=blueprint.description,
        framework=blueprint.recommended_framework,
        public_inputs=list(blueprint.public_inputs),
        private_inputs=list(blueprint.private_inputs),
        constraints=list(blueprint.constraints),
        produced_by=produced_by,
        cycle=cycle,
        complexity_budget=max(32, blueprint.constraint_count * 4),
    )


def serialize_public_inputs(public_inputs: dict[str, str]) -> list[str]:
    return [f'{key}={public_inputs[key]}' for key in sorted(public_inputs)]


def deterministic_commitments(circuit: Circuit, trace: Trace, witness: Witness) -> list[str]:
    sources = [
        {'kind': 'circuit', 'artifact_id': circuit.artifact_id, 'content_hash': circuit.content_hash()},
        {'kind': 'trace', 'artifact_id': trace.artifact_id, 'content_hash': trace.content_hash()},
        {'kind': 'witness', 'artifact_id': witness.artifact_id, 'content_hash': witness.content_hash()},
    ]
    return [sha256_hex(canonical_json(source)) for source in sources]


def _to_zk_witness(trace: Trace, witness: Witness) -> ZKWitness:
    return ZKWitness(
        public_inputs=witness.public_inputs,
        private_inputs=witness.private_inputs,
        trace_steps=trace.steps,
        input_hash=witness.input_hash,
        output_hash=witness.output_hash,
        trace_hash=witness.trace_hash,
    )


def prove_artifacts(circuit: Circuit, trace: Trace, witness: Witness, *, produced_by: str = 'performance_optimization', cycle: int = 1) -> Proof:
    zk_witness = _to_zk_witness(trace, witness)
    zk_proof = generate_zk_proof(zk_witness)
    metadata = {
        'verification_key_id': zk_proof.verification_key_id,
        'backend': 'sha256-deterministic-proof-stub',
        'compatibility': 'plonk,groth16,stark',
        'trace_artifact_id': trace.artifact_id,
    }
    return build_proof_artifact(
        proof_system='sha256-structured-stub',
        circuit_artifact_id=circuit.artifact_id,
        witness_artifact_id=witness.artifact_id,
        commitments=deterministic_commitments(circuit, trace, witness),
        public_inputs=serialize_public_inputs(witness.public_inputs),
        metadata=metadata,
        proof_blob_hex=zk_proof.proof_bytes.hex(),
        input_hash=witness.input_hash,
        output_hash=witness.output_hash,
        trace_hash=witness.trace_hash,
        final_proof=zk_proof.proof_bytes.hex(),
        produced_by=produced_by,
        cycle=cycle,
    )


def prove_request(request_payload: object, *, circuit: Circuit | None = None, produced_by: str = 'performance_optimization', cycle: int = 1) -> Proof:
    packet = build_trace_packet(request_payload, produced_by='backend_integration', cycle=cycle)
    selected_circuit = circuit or build_default_circuit_artifact(cycle=cycle)
    return prove_artifacts(selected_circuit, packet.trace_artifact, packet.witness_artifact, produced_by=produced_by, cycle=cycle)


def benchmark_stub_prover(iterations: int = 5) -> dict:
    circuit = build_default_circuit_artifact(cycle=1)
    packet = build_trace_packet(REFERENCE_REQUEST, produced_by='backend_integration', cycle=1)
    timings = []
    proof = None
    for _ in range(iterations):
        start = time.perf_counter()
        proof = prove_artifacts(circuit, packet.trace_artifact, packet.witness_artifact, produced_by='performance_optimization', cycle=1)
        timings.append((time.perf_counter() - start) * 1000)
    if proof is None:
        raise RuntimeError('Stub prover benchmark did not produce a proof')
    return {
        'iterations': iterations,
        'average_ms': round(mean(timings), 4),
        'max_ms': round(max(timings), 4),
        'min_ms': round(min(timings), 4),
        'verification_key_id': proof.metadata['verification_key_id'],
        'proof_system': proof.proof_system,
        'commitment_count': len(proof.commitments),
    }
