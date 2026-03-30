"""Validation tests for the real Halo2-backed PLONK path."""
from __future__ import annotations

import time
from decimal import Decimal, ROUND_HALF_UP

import pytest

from core.sample import REFERENCE_REQUEST


def test_1_intt_inverse_of_ntt():
  from zk.field_utils import FIELD_ORDER, OMEGA, intt, poly_eval

  coeffs = [1, 2, 3, 0, 0, 0, 0, 0]
  omega_pow = 1
  values = []
  for _ in range(8):
    values.append(poly_eval(coeffs, omega_pow))
    omega_pow = omega_pow * OMEGA % FIELD_ORDER
  recovered = intt(values)
  assert recovered == coeffs


def test_2_poly_eval_horner():
  from zk.field_utils import poly_eval

  coeffs = [5, 3, 1, 0, 0, 0, 0, 0]
  assert poly_eval(coeffs, 4) == 33


def test_3_poly_divmod_linear():
  from zk.field_utils import FIELD_ORDER, poly_divmod_linear, poly_eval

  coeffs = [6, -5, 1, 0, 0, 0, 0, 0]
  coeffs = [c % FIELD_ORDER for c in coeffs]
  z = 2
  v = poly_eval(coeffs, z)
  assert v == 0
  _, remainder = poly_divmod_linear(coeffs, z)
  assert remainder == v


def test_4_kzg_open_coeffs_correctness():
  from zk.field_utils import FIELD_ORDER, kzg_open_coeffs, poly_eval

  coeffs = [1, 2, 3, 1, 0, 0, 0, 0]
  z = 5
  v = poly_eval(coeffs, z)
  q = kzg_open_coeffs(coeffs, z, v)
  w = 7
  lhs = (w - z) * poly_eval(q, w) % FIELD_ORDER
  rhs = (poly_eval(coeffs, w) - v) % FIELD_ORDER
  assert lhs == rhs


def test_5_omega_is_primitive_8th_root():
  from zk.field_utils import FIELD_ORDER, N, OMEGA

  assert pow(OMEGA, N, FIELD_ORDER) == 1
  assert pow(OMEGA, N // 2, FIELD_ORDER) != 1


def test_6_intt_round_trip_random_poly():
  from zk.field_utils import FIELD_ORDER, OMEGA, intt, poly_eval

  original = [index * 12345 % FIELD_ORDER for index in range(1, 9)]
  omega_pow = 1
  values = []
  for _ in range(8):
    values.append(poly_eval(original, omega_pow))
    omega_pow = omega_pow * OMEGA % FIELD_ORDER
  recovered = intt(values)
  assert recovered == original


def test_7_domain_interpolation_matches_values():
  from zk.field_utils import FIELD_ORDER, OMEGA, intt, poly_eval

  values = [100, 200, 300, 400, 500, 600, 700, 800]
  coeffs = intt(values)
  omega_pow = 1
  for expected in values:
    got = poly_eval(coeffs, omega_pow)
    assert got == expected
    omega_pow = omega_pow * OMEGA % FIELD_ORDER


def test_8_compile_circuit_structure():
  from zk.compiler.plonk_adapter import PUBLIC_BINDING_TARGETS, compile_circuit

  circuit = compile_circuit()
  assert circuit.n_gates == 8
  assert len(circuit.gates) == 8
  assert len(circuit.public_binding_targets) == len(PUBLIC_BINDING_TARGETS)
  for index in range(5):
    assert circuit.selector_q_M[index] == 1
    assert circuit.selector_q_L[index] == 0
  for index in range(5, 8):
    assert circuit.selector_q_L[index] == 1
    assert circuit.selector_q_R[index] == 1
    assert circuit.selector_q_M[index] == 0


def test_9_circuit_hash_is_deterministic():
  from zk.compiler.plonk_adapter import compile_circuit

  assert compile_circuit().circuit_hash == compile_circuit().circuit_hash


def test_10_circuit_q_o_all_minus_one():
  from zk.compiler.plonk_adapter import compile_circuit
  from zk.field_utils import FIELD_ORDER

  circuit = compile_circuit()
  for index in range(8):
    assert circuit.selector_q_O[index] == FIELD_ORDER - 1


def test_11_gate_constraints_satisfied_for_reference():
  from backend.trace_adapter import build_trace_packet
  from zk.witness.generator import generate_assignment

  packet = build_trace_packet(REFERENCE_REQUEST)
  assignment = generate_assignment(packet.witness_artifact)
  assert all(assignment.verify_gate_constraints())


def test_12_gate_constraints_deterministic():
  from backend.trace_adapter import build_trace_packet
  from zk.witness.generator import generate_assignment

  packet = build_trace_packet(REFERENCE_REQUEST)
  assignment_1 = generate_assignment(packet.witness_artifact)
  assignment_2 = generate_assignment(packet.witness_artifact)
  assert assignment_1.a_col == assignment_2.a_col
  assert assignment_1.b_col == assignment_2.b_col
  assert assignment_1.c_col == assignment_2.c_col
  assert assignment_1.public_inputs_hash == assignment_2.public_inputs_hash


def test_13_landed_cost_in_output_wire():
  from backend.trace_adapter import build_trace_packet
  from zk.field_utils import FIELD_ORDER
  from zk.witness.generator import FIXED_POINT_SCALE, generate_assignment

  packet = build_trace_packet(REFERENCE_REQUEST)
  assignment = generate_assignment(packet.witness_artifact)
  expected_fp = int(
    (Decimal(packet.witness_artifact.public_inputs['landed_cost']) * FIXED_POINT_SCALE).to_integral_value(
      rounding=ROUND_HALF_UP
    )
  )
  assert assignment.c_col[7] == expected_fp % FIELD_ORDER


@pytest.fixture(scope='module')
def reference_proof():
  from backend.trace_adapter import build_trace_packet
  from zk.provers.plonk_prover import build_plonk_proof

  packet = build_trace_packet(REFERENCE_REQUEST)
  proof = build_plonk_proof(
    packet.witness_artifact,
    packet.trace_artifact.trace_hash,
    produced_by='test_prover',
    cycle=1,
  )
  return proof, packet


def test_14_proof_blob_non_empty(reference_proof):
  proof, _ = reference_proof
  assert len(proof.proof_blob_hex) > 0
  assert len(proof.proof_blob_hex) % 2 == 0


def test_15_proof_is_deterministic(reference_proof):
  from zk.provers.plonk_prover import build_plonk_proof

  proof_1, packet = reference_proof
  proof_2 = build_plonk_proof(
    packet.witness_artifact,
    packet.trace_artifact.trace_hash,
    produced_by='test_prover',
    cycle=1,
  )
  assert proof_1.proof_blob_hex == proof_2.proof_blob_hex
  assert proof_1.final_proof == proof_2.final_proof


def test_16_proof_system_label(reference_proof):
  proof, _ = reference_proof
  assert proof.proof_system == 'plonk'


def test_17_valid_proof_verifies(reference_proof):
  from zk.verifiers.plonk_verifier import verify_plonk_proof

  proof, _ = reference_proof
  result = verify_plonk_proof(proof, produced_by='test_verifier', cycle=1)
  assert result.status == 'VALID', result.reason
  assert 'halo2_verification_ok' in result.checks


def test_18_tampered_proof_fails(reference_proof):
  from utils.hashing import sha256_hex
  from zk.interfaces import build_proof_artifact
  from zk.verifiers.plonk_verifier import verify_plonk_proof

  proof, _ = reference_proof
  blob = bytearray(bytes.fromhex(proof.proof_blob_hex))
  blob[len(blob) // 2] ^= 0xFF
  tampered_hex = blob.hex()
  tampered_proof = build_proof_artifact(
    proof_system=proof.proof_system,
    circuit_artifact_id=proof.circuit_artifact_id,
    witness_artifact_id=proof.witness_artifact_id,
    commitments=proof.commitments,
    public_inputs=proof.public_inputs,
    metadata=proof.metadata,
    proof_blob_hex=tampered_hex,
    input_hash=proof.input_hash,
    output_hash=proof.output_hash,
    trace_hash=proof.trace_hash,
    final_proof=sha256_hex(tampered_hex),
    produced_by='test_tamper',
    cycle=1,
  )
  result = verify_plonk_proof(tampered_proof, produced_by='test_verifier', cycle=1)
  assert result.status == 'INVALID'


def test_19_wrong_proof_system_rejected(reference_proof):
  from zk.interfaces import build_proof_artifact
  from zk.verifiers.plonk_verifier import verify_plonk_proof

  proof, _ = reference_proof
  wrong_system_proof = build_proof_artifact(
    proof_system='sha256-structured-stub',
    circuit_artifact_id=proof.circuit_artifact_id,
    witness_artifact_id=proof.witness_artifact_id,
    commitments=proof.commitments,
    public_inputs=proof.public_inputs,
    metadata=proof.metadata,
    proof_blob_hex=proof.proof_blob_hex,
    input_hash=proof.input_hash,
    output_hash=proof.output_hash,
    trace_hash=proof.trace_hash,
    final_proof=proof.final_proof,
    produced_by='test',
    cycle=1,
  )
  result = verify_plonk_proof(wrong_system_proof, produced_by='test_verifier', cycle=1)
  assert result.status == 'INVALID'
  assert 'proof_system_check_failed' in result.checks


def test_20_trace_hash_mismatch_rejected():
  from backend.trace_adapter import build_trace_packet
  from zk.provers.plonk_prover import build_plonk_proof

  packet = build_trace_packet(REFERENCE_REQUEST)
  with pytest.raises(ValueError, match='trace_hash'):
    build_plonk_proof(packet.witness_artifact, 'deadbeef' * 8, produced_by='test_prover', cycle=1)


def test_21_wrong_circuit_binding_fails(reference_proof):
  from utils.hashing import sha256_hex
  from zk.interfaces import build_proof_artifact
  from zk.verifiers.plonk_verifier import verify_plonk_proof

  proof, _ = reference_proof
  bad_metadata = dict(proof.metadata)
  bad_metadata['circuit_hash'] = '0' * 64
  tampered_proof = build_proof_artifact(
    proof_system=proof.proof_system,
    circuit_artifact_id=proof.circuit_artifact_id,
    witness_artifact_id=proof.witness_artifact_id,
    commitments=proof.commitments,
    public_inputs=proof.public_inputs,
    metadata=bad_metadata,
    proof_blob_hex=proof.proof_blob_hex,
    input_hash=proof.input_hash,
    output_hash=proof.output_hash,
    trace_hash=proof.trace_hash,
    final_proof=sha256_hex(proof.proof_blob_hex),
    produced_by='test_tamper',
    cycle=1,
  )
  result = verify_plonk_proof(tampered_proof, produced_by='test_verifier', cycle=1)
  assert result.status == 'INVALID'
  assert 'circuit_hash_binding_mismatch' in result.checks


def test_22_different_inputs_produce_different_proofs():
  from backend.trace_adapter import build_trace_packet
  from zk.provers.plonk_prover import build_plonk_proof

  variant = dict(REFERENCE_REQUEST)
  variant['quantity'] = REFERENCE_REQUEST['quantity'] + 1
  packet_1 = build_trace_packet(REFERENCE_REQUEST)
  packet_2 = build_trace_packet(variant)
  proof_1 = build_plonk_proof(packet_1.witness_artifact, packet_1.trace_artifact.trace_hash)
  proof_2 = build_plonk_proof(packet_2.witness_artifact, packet_2.trace_artifact.trace_hash)
  assert proof_1.proof_blob_hex != proof_2.proof_blob_hex
  assert proof_1.final_proof != proof_2.final_proof


def test_23_proof_queue_complete():
  from backend.proof_queue import ProofQueue
  from backend.trace_adapter import build_trace_packet

  queue = ProofQueue(max_workers=1)
  packet = build_trace_packet(REFERENCE_REQUEST)
  task_id = queue.submit(
    packet.witness_artifact,
    packet.trace_artifact.trace_hash,
    produced_by='test_queue',
    cycle=1,
    auto_verify=True,
  )

  deadline = time.monotonic() + 60.0
  task = None
  while time.monotonic() < deadline:
    task = queue.get_task(task_id)
    if task is not None and task.status in {'completed', 'failed'}:
      break
    time.sleep(0.5)

  assert task is not None
  assert task.status == 'completed', f'Task failed: {task.error}'
  assert task.result is not None
  assert task.result.proof_system == 'plonk'
  assert task.verification is not None
  assert task.verification.status == 'VALID'
  queue.shutdown(wait=False)


def test_24_proof_queue_snapshot():
  from backend.proof_queue import ProofQueue

  queue = ProofQueue(max_workers=1)
  snap = queue.snapshot()
  assert snap['total'] == 0
  queue.shutdown(wait=False)


def test_25_fast_stub_path_timing():
  from zk.provers.stub_prover import prove_request

  start = time.perf_counter()
  proof = prove_request(REFERENCE_REQUEST)
  elapsed_ms = (time.perf_counter() - start) * 1000
  assert elapsed_ms < 50, f'Fast path too slow: {elapsed_ms:.1f}ms'
  assert proof.proof_system == 'sha256-structured-stub'


def test_26_plonk_prover_imports_without_circular_failure():
  import importlib

  module = importlib.import_module('zk.provers.plonk_prover')
  assert hasattr(module, 'build_plonk_proof')


def test_27_native_backend_failures_do_not_fallback_to_python_stub(monkeypatch):
  import zk.rust_bridge as rust_bridge

  def _raise() -> None:
    raise RuntimeError('backend missing')

  monkeypatch.setattr(rust_bridge, 'ensure_backend_binary', _raise)
  with pytest.raises(RuntimeError, match='native Halo2 backend unavailable'):
    rust_bridge.run_backend('prove', {})
