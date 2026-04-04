from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.engine import calculate_import_landed_cost
from core.zk_interface import ZKWitness, extract_witness
from models.schemas import CalculationResponse, ImportCalculationRequest
from zk.interfaces import Trace, Witness, build_trace_artifact, build_witness_artifact


@dataclass(frozen=True)
class DeterministicTracePacket:
    request: ImportCalculationRequest
    response: CalculationResponse
    witness: ZKWitness
    trace_artifact: Trace
    witness_artifact: Witness

    def summary(self) -> dict[str, Any]:
        return {
            'input_hash': self.response.integrity.input_hash,
            'output_hash': self.response.integrity.output_hash,
            'trace_hash': self.response.integrity.trace_hash,
            'integrity_hash': self.response.integrity.integrity_hash,
            'trace_length': len(self.response.trace),
            'trace_artifact_id': self.trace_artifact.artifact_id,
            'witness_artifact_id': self.witness_artifact.artifact_id,
            'public_inputs': self.witness_artifact.public_inputs,
        }


def build_trace_packet(request_payload: object, *, produced_by: str = 'backend_integration', cycle: int = 1) -> DeterministicTracePacket:
    request = ImportCalculationRequest.model_validate(request_payload)
    response = calculate_import_landed_cost(request)
    witness = extract_witness(request, response)
    trace_artifact = build_trace_artifact(
        input_hash=response.integrity.input_hash,
        steps=response.trace,
        produced_by=produced_by,
        cycle=cycle,
    )
    witness_artifact = build_witness_artifact(
        trace_artifact_id=trace_artifact.artifact_id,
        input_hash=response.integrity.input_hash,
        output_hash=response.integrity.output_hash,
        trace_hash=trace_artifact.trace_hash,
        public_inputs={key: str(value) for key, value in sorted(witness.public_inputs.items())},
        private_inputs=request.model_dump(mode='python'),
        produced_by=produced_by,
        cycle=cycle,
    )
    if response.integrity.trace_hash != trace_artifact.trace_hash:
        raise RuntimeError('Trace artifact hash diverged from deterministic engine proof trace hash')
    if response.integrity.input_hash != witness_artifact.input_hash or response.integrity.output_hash != witness_artifact.output_hash:
        raise RuntimeError('Witness artifact hashes diverged from deterministic engine proof hashes')
    return DeterministicTracePacket(
        request=request,
        response=response,
        witness=witness,
        trace_artifact=trace_artifact,
        witness_artifact=witness_artifact,
    )
