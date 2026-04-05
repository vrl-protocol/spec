from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.trace_adapter import build_trace_packet
from core.sample import REFERENCE_REQUEST
from zk.interfaces import Circuit, Proof, Trace, VerificationResult, Witness, summarize_artifact
from zk.provers.stub_prover import benchmark_stub_prover, build_default_circuit_artifact, prove_artifacts
from zk.verifiers.stub_verifier import verify_artifacts


@dataclass(frozen=True)
class ZKPipelineBundle:
    circuit: Circuit
    trace: Trace
    witness: Witness
    proof: Proof
    verification_result: VerificationResult
    artifacts: dict[str, str]

    @property
    def input_hash(self) -> str:
        return self.proof.input_hash

    @property
    def output_hash(self) -> str:
        return self.proof.output_hash

    @property
    def trace_hash(self) -> str:
        return self.proof.trace_hash

    @property
    def final_proof(self) -> str:
        return self.proof.final_proof

    @property
    def proof_hex(self) -> str:
        return self.proof.proof_blob_hex

    @property
    def verified(self) -> bool:
        return self.verification_result.status == 'VALID'

    @property
    def verification_key_id(self) -> str:
        return self.proof.metadata['verification_key_id']

    @property
    def public_inputs(self) -> dict[str, str]:
        return self.witness.public_inputs

    @property
    def trace_length(self) -> int:
        return len(self.trace.steps)

    def summary(self) -> dict[str, Any]:
        return {
            'input_hash': self.input_hash,
            'output_hash': self.output_hash,
            'trace_hash': self.trace_hash,
            'final_proof': self.final_proof,
            'proof_hex': self.proof_hex,
            'verified': self.verified,
            'verification_key_id': self.verification_key_id,
            'public_inputs': self.public_inputs,
            'trace_length': self.trace_length,
            'artifacts': self.artifacts,
            'artifact_ids': {
                'circuit': self.circuit.artifact_id,
                'trace': self.trace.artifact_id,
                'witness': self.witness.artifact_id,
                'proof': self.proof.artifact_id,
                'verification_result': self.verification_result.artifact_id,
            },
        }


def build_stub_pipeline_bundle(request_payload: object, *, cycle: int = 1) -> ZKPipelineBundle:
    circuit = build_default_circuit_artifact(cycle=cycle)
    packet = build_trace_packet(request_payload, produced_by='backend_integration', cycle=cycle)
    proof = prove_artifacts(circuit, packet.trace_artifact, packet.witness_artifact, produced_by='performance_optimization', cycle=cycle)
    verification_result = verify_artifacts(circuit, packet.trace_artifact, packet.witness_artifact, proof, produced_by='verifier_agent', cycle=cycle)
    return ZKPipelineBundle(
        circuit=circuit,
        trace=packet.trace_artifact,
        witness=packet.witness_artifact,
        proof=proof,
        verification_result=verification_result,
        artifacts={
            'trace_adapter': 'backend/trace_adapter.py',
            'stub_prover': 'zk/provers/stub_prover.py',
            'stub_verifier': 'zk/verifiers/stub_verifier.py',
            'circuit': summarize_artifact(circuit)['artifact_id'],
            'trace': summarize_artifact(packet.trace_artifact)['artifact_id'],
            'witness': summarize_artifact(packet.witness_artifact)['artifact_id'],
            'proof': summarize_artifact(proof)['artifact_id'],
            'verification_result': summarize_artifact(verification_result)['artifact_id'],
        },
    )


def compare_repeated_runs(request_payload: object, iterations: int = 3) -> dict[str, Any]:
    bundles = [build_stub_pipeline_bundle(request_payload, cycle=1) for _ in range(iterations)]
    first = bundles[0]
    all_equal = all(bundle.summary() == first.summary() for bundle in bundles[1:])
    return {
        'iterations': iterations,
        'all_equal': all_equal,
        'reference': first.summary(),
        'runs': [bundle.summary() for bundle in bundles],
    }


def simulate_input_variants() -> dict[str, Any]:
    same_input = compare_repeated_runs(REFERENCE_REQUEST, iterations=3)
    variant_payload = dict(REFERENCE_REQUEST)
    variant_payload['quantity'] = variant_payload['quantity'] + 1
    variant_bundle = build_stub_pipeline_bundle(variant_payload, cycle=1)
    baseline_bundle = build_stub_pipeline_bundle(REFERENCE_REQUEST, cycle=1)
    return {
        'same_input_consistent': same_input['all_equal'],
        'baseline_input_hash': baseline_bundle.input_hash,
        'variant_input_hash': variant_bundle.input_hash,
        'hashes_differ_for_variant': baseline_bundle.input_hash != variant_bundle.input_hash,
        'baseline_final_proof': baseline_bundle.final_proof,
        'variant_final_proof': variant_bundle.final_proof,
        'benchmark': benchmark_stub_prover(iterations=3),
    }
