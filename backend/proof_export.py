from __future__ import annotations
from pathlib import Path
from typing import Any

from backend.trace_adapter import DeterministicTracePacket, build_trace_packet
from utils.canonical import canonical_json
from utils.hashing import constant_time_equal, sha256_hex
from zk.compiler.plonk_adapter import compile_circuit
from zk.interfaces import Proof
from zk.keys.manager import KeyManager
from zk.provers.plonk_prover import build_plonk_proof
from zk.verifiers.plonk_verifier import verify_plonk_proof


def _canonical_proof_payload(proof: Proof) -> dict[str, Any]:
  payload = proof.model_dump(mode='json')
  payload.pop('proof_bytes', None)
  payload.pop('proving_system', None)
  payload.pop('circuit_hash', None)
  return payload


def _verification_key_hash(circuit_hash: str) -> str:
  verification_key = KeyManager.derive_verification_key(circuit_hash)
  manifest_bytes = verification_key.manifest_path.read_bytes()
  return sha256_hex(manifest_bytes)


def export_proof_bundle(input_payload: dict[str, Any], *, packet: DeterministicTracePacket | None = None, proof: Proof | None = None) -> dict[str, Any]:
  resolved_packet = packet or build_trace_packet(input_payload, produced_by='proof_export', cycle=1)
  resolved_proof = proof or build_plonk_proof(
    resolved_packet.witness_artifact,
    resolved_packet.trace_artifact.trace_hash,
    produced_by='proof_export',
    cycle=1,
  )
  circuit = compile_circuit()
  verification_key_hash = _verification_key_hash(circuit.circuit_hash)
  return {
    'input': resolved_packet.request.model_dump(mode='json'),
    'input_hash': resolved_packet.response.proof.input_hash,
    'output_hash': resolved_packet.response.proof.output_hash,
    'trace_hash': resolved_packet.trace_artifact.trace_hash,
    'circuit_hash': circuit.circuit_hash,
    'verification_key_hash': verification_key_hash,
    'proof': _canonical_proof_payload(resolved_proof),
  }


def write_proof_bundle(path: Path | str, bundle: dict[str, Any]) -> Path:
  target = Path(path)
  target.parent.mkdir(parents=True, exist_ok=True)
  target.write_text(canonical_json(bundle), encoding='utf-8')
  return target


def export_and_write_proof_bundle(path: Path | str, input_payload: dict[str, Any]) -> Path:
  bundle = export_proof_bundle(input_payload)
  return write_proof_bundle(path, bundle)


def verify_proof_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
  input_payload = bundle['input']
  packet = build_trace_packet(input_payload, produced_by='proof_bundle_verify', cycle=1)
  circuit = compile_circuit()

  expected_input_hash = packet.response.proof.input_hash
  expected_output_hash = packet.response.proof.output_hash
  expected_trace_hash = packet.trace_artifact.trace_hash
  expected_circuit_hash = circuit.circuit_hash
  expected_vk_hash = _verification_key_hash(circuit.circuit_hash)

  proof_payload = bundle['proof']
  for field_name in ('proof_bytes', 'proving_system', 'circuit_hash'):
    proof_payload.pop(field_name, None)
  proof = Proof.model_validate(proof_payload)

  checks: list[str] = []
  valid = True
  reason = 'bundle verified successfully'

  if not constant_time_equal(bundle['input_hash'], expected_input_hash):
    valid = False
    checks.append('input_hash_mismatch')
  else:
    checks.append('input_hash_ok')

  if not constant_time_equal(bundle['output_hash'], expected_output_hash):
    valid = False
    checks.append('output_hash_mismatch')
  else:
    checks.append('output_hash_ok')

  if not constant_time_equal(bundle['trace_hash'], expected_trace_hash):
    valid = False
    checks.append('trace_hash_mismatch')
  else:
    checks.append('trace_hash_ok')

  if not constant_time_equal(bundle['circuit_hash'], expected_circuit_hash):
    valid = False
    checks.append('circuit_hash_mismatch')
  else:
    checks.append('circuit_hash_ok')

  if not constant_time_equal(bundle['verification_key_hash'], expected_vk_hash):
    valid = False
    checks.append('verification_key_hash_mismatch')
  else:
    checks.append('verification_key_hash_ok')

  if valid:
    verification = verify_plonk_proof(proof, produced_by='proof_bundle_verify', cycle=1)
    if verification.status != 'VALID':
      valid = False
      reason = verification.reason
      checks.extend(verification.checks)
    else:
      checks.extend(verification.checks)
  else:
    reason = 'bundle hash binding mismatch'

  return {
    'valid': valid,
    'reason': reason,
    'checks': checks,
    'input_hash': expected_input_hash,
    'trace_hash': expected_trace_hash,
    'circuit_hash': expected_circuit_hash,
    'verification_key_hash': expected_vk_hash,
  }
