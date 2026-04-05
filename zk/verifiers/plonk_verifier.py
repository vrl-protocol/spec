from __future__ import annotations

from utils.canonical import canonical_json
from utils.hashing import constant_time_equal, sha256_hex
from zk.compiler.plonk_adapter import compile_circuit
from zk.interfaces import Proof, VerificationResult, build_verification_artifact
from zk.keys.manager import KeyManager
from zk.rust_bridge import KEY_ROOT, run_backend
from zk.witness.generator import build_instance_values, canonical_public_inputs_hash, to_fixed_point

_SUPPORTED_PROOF_SYSTEM = 'plonk'
_VERIFIER_BACKEND = 'halo2-plonk-pasta-v1-verifier'


def _invalid_result(proof: Proof, *, reason: str, checks: list[str], metadata: dict[str, str] | None = None, produced_by: str, cycle: int) -> VerificationResult:
  return build_verification_artifact(
    subject_artifact_id=proof.artifact_id,
    verifier_backend=_VERIFIER_BACKEND,
    status='INVALID',
    reason=reason,
    checks=checks,
    metadata=metadata or {},
    produced_by=produced_by,
    cycle=cycle,
  )


def _parse_public_inputs(entries: list[str]) -> dict[str, str]:
  public_inputs: dict[str, str] = {}
  for entry in entries:
    if '=' not in entry:
      raise ValueError(f'invalid public input entry: {entry!r}')
    key, value = entry.split('=', 1)
    if not key:
      raise ValueError(f'invalid public input key: {entry!r}')
    public_inputs[key] = value
  return dict(sorted(public_inputs.items()))


def _final_proof_hash(*, proof_blob_hex: str, commitments: list[str], public_inputs: list[str], circuit_hash: str, trace_hash: str, public_inputs_hash: str) -> str:
  payload = {
    'proof_bytes': proof_blob_hex,
    'commitments': commitments,
    'public_inputs': public_inputs,
    'proving_system': _SUPPORTED_PROOF_SYSTEM,
    'circuit_hash': circuit_hash,
    'trace_hash': trace_hash,
    'public_inputs_hash': public_inputs_hash,
  }
  return sha256_hex(canonical_json(payload))


def verify_plonk_proof(proof: Proof, *, produced_by: str = 'plonk_verifier', cycle: int = 1) -> VerificationResult:
  checks: list[str] = []
  metadata = {
    'proof_system': proof.proof_system,
    'circuit_hash': proof.metadata.get('circuit_hash', ''),
  }

  if proof.proof_system != _SUPPORTED_PROOF_SYSTEM:
    return _invalid_result(
      proof,
      reason=f'unsupported proof_system: {proof.proof_system!r}',
      checks=['proof_system_check_failed'],
      metadata=metadata,
      produced_by=produced_by,
      cycle=cycle,
    )

  try:
    public_inputs = _parse_public_inputs(proof.public_inputs)
    checks.append('public_inputs_parse_ok')

    if 'landed_cost' not in public_inputs:
      return _invalid_result(
        proof,
        reason='missing landed_cost public input',
        checks=checks + ['landed_cost_public_input_missing'],
        metadata=metadata,
        produced_by=produced_by,
        cycle=cycle,
      )

    circuit = compile_circuit()
    checks.append('circuit_compile_ok')

    if proof.metadata.get('circuit_hash', '') != circuit.circuit_hash or proof.circuit_hash != circuit.circuit_hash:
      return _invalid_result(
        proof,
        reason='circuit_hash binding mismatch',
        checks=checks + ['circuit_hash_binding_mismatch'],
        metadata={**metadata, 'expected_circuit_hash': circuit.circuit_hash},
        produced_by=produced_by,
        cycle=cycle,
      )
    checks.append('circuit_hash_binding_ok')

    if proof.metadata.get('trace_hash', proof.trace_hash) != proof.trace_hash:
      return _invalid_result(
        proof,
        reason='trace_hash metadata mismatch',
        checks=checks + ['trace_hash_binding_mismatch'],
        metadata=metadata,
        produced_by=produced_by,
        cycle=cycle,
      )
    checks.append('trace_hash_binding_ok')

    public_inputs_hash = canonical_public_inputs_hash(public_inputs)
    if not constant_time_equal(public_inputs_hash, proof.metadata.get('public_inputs_hash', '')):
      return _invalid_result(
        proof,
        reason='public_inputs_hash binding mismatch',
        checks=checks + ['public_inputs_hash_binding_mismatch'],
        metadata={**metadata, 'expected_public_inputs_hash': public_inputs_hash},
        produced_by=produced_by,
        cycle=cycle,
      )
    checks.append('public_inputs_hash_binding_ok')

    expected_final_proof = _final_proof_hash(
      proof_blob_hex=proof.proof_blob_hex,
      commitments=proof.commitments,
      public_inputs=proof.public_inputs,
      circuit_hash=circuit.circuit_hash,
      trace_hash=proof.trace_hash,
      public_inputs_hash=public_inputs_hash,
    )
    if not constant_time_equal(expected_final_proof, proof.final_proof):
      return _invalid_result(
        proof,
        reason='final_proof binding mismatch',
        checks=checks + ['final_proof_binding_mismatch'],
        metadata=metadata,
        produced_by=produced_by,
        cycle=cycle,
      )
    checks.append('final_proof_binding_ok')

    verification_key = KeyManager.derive_verification_key(circuit.circuit_hash, circuit=circuit)
    if proof.metadata.get('verification_key_id') and proof.metadata['verification_key_id'] != verification_key.verification_key_id:
      return _invalid_result(
        proof,
        reason='verification_key binding mismatch',
        checks=checks + ['verification_key_binding_mismatch'],
        metadata={**metadata, 'expected_verification_key_id': verification_key.verification_key_id},
        produced_by=produced_by,
        cycle=cycle,
      )
    checks.append('verification_key_binding_ok')

    landed_cost_fp = to_fixed_point(public_inputs['landed_cost'])
    instance_values = build_instance_values(
      landed_cost_fp,
      proof.trace_hash,
      circuit.circuit_hash,
      public_inputs_hash,
    )
    backend_response = run_backend(
      'verify',
      {
        'circuit_hash': circuit.circuit_hash,
        'trace_hash': proof.trace_hash,
        'public_inputs_hash': public_inputs_hash,
        'proof_bytes_hex': proof.proof_blob_hex,
        'instance_values': [str(value) for value in instance_values],
        'key_root': str(KEY_ROOT),
      },
      timeout=300,
    )
    backend_checks = [str(item) for item in backend_response.get('checks', [])]
    checks.extend(backend_checks)
    backend_metadata = {str(key): str(value) for key, value in backend_response.get('metadata', {}).items()}

    if not backend_response.get('valid', False):
      return _invalid_result(
        proof,
        reason=str(backend_response.get('reason', 'Halo2 verification failed')),
        checks=checks + ['halo2_verification_failed'],
        metadata={**metadata, **backend_metadata},
        produced_by=produced_by,
        cycle=cycle,
      )

    checks.append('halo2_verification_ok')
    return build_verification_artifact(
      subject_artifact_id=proof.artifact_id,
      verifier_backend=_VERIFIER_BACKEND,
      status='VALID',
      reason=str(backend_response.get('reason', 'Halo2 proof verified')),
      checks=checks,
      metadata={**metadata, **backend_metadata},
      produced_by=produced_by,
      cycle=cycle,
    )
  except Exception as exc:
    return _invalid_result(
      proof,
      reason=f'verification backend error: {exc}',
      checks=checks + ['verification_backend_error'],
      metadata=metadata,
      produced_by=produced_by,
      cycle=cycle,
    )
