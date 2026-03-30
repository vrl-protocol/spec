from __future__ import annotations

from utils.canonical import canonical_json
from utils.hashing import sha256_hex
from zk.compiler.plonk_adapter import compile_circuit
from zk.interfaces import Proof, Witness, build_proof_artifact
from zk.keys.manager import KeyManager
from zk.rust_bridge import BACKEND_VERSION, KEY_ROOT, run_backend
from zk.witness.generator import build_instance_values, generate_assignment

_PROOF_SYSTEM = 'plonk'


def serialize_public_inputs(public_inputs: dict[str, str]) -> list[str]:
  return [f'{key}={public_inputs[key]}' for key in sorted(public_inputs)]


def _assert_witness_trace_match(witness_artifact: Witness, expected_trace_hash: str) -> None:
  if witness_artifact.trace_hash != expected_trace_hash:
    raise ValueError(
      f'witness_artifact.trace_hash {witness_artifact.trace_hash!r} != expected trace_hash {expected_trace_hash!r}'
    )


def _final_proof_hash(*, proof_blob_hex: str, commitments: list[str], public_inputs: list[str], circuit_hash: str, trace_hash: str, public_inputs_hash: str) -> str:
  payload = {
    'proof_bytes': proof_blob_hex,
    'commitments': commitments,
    'public_inputs': public_inputs,
    'proving_system': _PROOF_SYSTEM,
    'circuit_hash': circuit_hash,
    'trace_hash': trace_hash,
    'public_inputs_hash': public_inputs_hash,
  }
  return sha256_hex(canonical_json(payload))


def build_plonk_proof(witness_artifact: Witness, trace_hash: str, *, produced_by: str = 'plonk_prover', cycle: int = 1) -> Proof:
  _assert_witness_trace_match(witness_artifact, trace_hash)

  circuit = compile_circuit()
  key_material = KeyManager.ensure_compiled(circuit)
  assignment = generate_assignment(witness_artifact)
  landed_cost_fp = assignment.wire_map['landed_cost_fp']
  instance_values = build_instance_values(
    landed_cost_fp,
    trace_hash,
    circuit.circuit_hash,
    assignment.public_inputs_hash,
  )
  response = run_backend(
    'prove',
    {
      'input_hash': witness_artifact.input_hash,
      'output_hash': witness_artifact.output_hash,
      'circuit_hash': circuit.circuit_hash,
      'trace_hash': trace_hash,
      'public_inputs_hash': assignment.public_inputs_hash,
      'witness_hash': witness_artifact.witness_hash,
      'a_col': [str(value) for value in assignment.a_col],
      'b_col': [str(value) for value in assignment.b_col],
      'c_col': [str(value) for value in assignment.c_col],
      'instance_values': [str(value) for value in instance_values],
      'key_root': str(KEY_ROOT),
    },
    timeout=300,
  )

  proof_blob_hex = str(response['proof_bytes_hex'])
  commitments = [str(item) for item in response.get('commitments', [])]
  public_inputs_list = serialize_public_inputs(witness_artifact.public_inputs)
  final_proof = _final_proof_hash(
    proof_blob_hex=proof_blob_hex,
    commitments=commitments,
    public_inputs=public_inputs_list,
    circuit_hash=circuit.circuit_hash,
    trace_hash=trace_hash,
    public_inputs_hash=assignment.public_inputs_hash,
  )

  backend_metadata = {str(key): str(value) for key, value in response.get('metadata', {}).items()}
  metadata = {
    'backend_version': backend_metadata.get('backend_version', BACKEND_VERSION),
    'backend': 'halo2-rust-subprocess',
    'circuit': circuit.version,
    'circuit_hash': circuit.circuit_hash,
    'trace_hash': trace_hash,
    'public_inputs_hash': assignment.public_inputs_hash,
    'params_k': backend_metadata.get('params_k', str(key_material.params_k)),
    'proving_key_id': backend_metadata.get('proving_key_id', key_material.proving_key_id),
    'verification_key_id': backend_metadata.get('verification_key_id', key_material.verification_key_id),
    'trace_artifact_id': witness_artifact.trace_artifact_id,
    'witness_hash': witness_artifact.witness_hash,
  }

  return build_proof_artifact(
    proof_system=_PROOF_SYSTEM,
    circuit_artifact_id=f'circuit_{circuit.circuit_hash[:24]}',
    witness_artifact_id=witness_artifact.artifact_id,
    commitments=commitments,
    public_inputs=public_inputs_list,
    metadata=metadata,
    proof_blob_hex=proof_blob_hex,
    input_hash=witness_artifact.input_hash,
    output_hash=witness_artifact.output_hash,
    trace_hash=trace_hash,
    final_proof=final_proof,
    produced_by=produced_by,
    cycle=cycle,
  )
