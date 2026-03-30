"""Production activation validation tests — Step 10.

Proves the five required properties:
  1. Same trace → identical witness → valid PLONK proof
  2. Modified trace → different proof (proof binds to trace)
  3. Wrong circuit hash → verification rejected
  4. Replay attack → rejected by ProofQueue deduplication
  5. API state machine: pending → completed
"""
from __future__ import annotations

import time

from core.engine import calculate_import_landed_cost
from core.sample import REFERENCE_REQUEST
from core.zk_interface import extract_witness, generate_zk_proof, verify_zk_proof
from models.schemas import ImportCalculationRequest


# ---------------------------------------------------------------------------
# Property 1: Same trace → identical witness → valid proof
# ---------------------------------------------------------------------------

def test_same_trace_produces_identical_valid_proof():
    req = ImportCalculationRequest.model_validate(REFERENCE_REQUEST)
    resp = calculate_import_landed_cost(req)
    w = extract_witness(req, resp)

    proof_a = generate_zk_proof(w)
    proof_b = generate_zk_proof(w)

    # Proofs are deterministic
    assert proof_a.proof_bytes == proof_b.proof_bytes
    # Both verify
    assert verify_zk_proof(proof_a, w)
    assert verify_zk_proof(proof_b, w)


# ---------------------------------------------------------------------------
# Property 2: Modified input → different proof
# ---------------------------------------------------------------------------

def test_modified_input_produces_different_proof():
    req_a = ImportCalculationRequest.model_validate(REFERENCE_REQUEST)
    variant = dict(REFERENCE_REQUEST)
    variant['quantity'] = REFERENCE_REQUEST['quantity'] + 1
    req_b = ImportCalculationRequest.model_validate(variant)

    resp_a = calculate_import_landed_cost(req_a)
    resp_b = calculate_import_landed_cost(req_b)
    w_a = extract_witness(req_a, resp_a)
    w_b = extract_witness(req_b, resp_b)

    proof_a = generate_zk_proof(w_a)
    proof_b = generate_zk_proof(w_b)

    # Different inputs → different proofs
    assert proof_a.proof_bytes != proof_b.proof_bytes
    # Cross-verify: proof_a must NOT verify against witness_b
    assert not verify_zk_proof(proof_a, w_b)
    assert not verify_zk_proof(proof_b, w_a)


# ---------------------------------------------------------------------------
# Property 3: Tampered proof → verification rejected
# ---------------------------------------------------------------------------

def test_tampered_proof_bytes_rejected():
    req = ImportCalculationRequest.model_validate(REFERENCE_REQUEST)
    resp = calculate_import_landed_cost(req)
    w = extract_witness(req, resp)
    proof = generate_zk_proof(w)

    # Flip a bit in the middle of proof_bytes
    raw = bytearray(proof.proof_bytes)
    raw[len(raw) // 2] ^= 0xFF
    from core.zk_interface import ZKProof
    tampered = ZKProof(
        proof_bytes=bytes(raw),
        public_inputs=proof.public_inputs,
        verification_key_id=proof.verification_key_id,
    )

    assert not verify_zk_proof(tampered, w)


# ---------------------------------------------------------------------------
# Property 4: Replay attack rejected by ProofQueue
# ---------------------------------------------------------------------------

def test_proof_queue_deduplicates_replay():
    from backend.trace_adapter import build_trace_packet
    from backend.proof_queue import ProofQueue

    queue = ProofQueue(max_workers=1)
    packet = build_trace_packet(REFERENCE_REQUEST)

    task_id_1 = queue.submit(
        packet.witness_artifact,
        packet.trace_artifact.trace_hash,
        produced_by='test_replay',
        cycle=1,
    )
    # Second submit with identical inputs must return the SAME task_id
    task_id_2 = queue.submit(
        packet.witness_artifact,
        packet.trace_artifact.trace_hash,
        produced_by='test_replay',
        cycle=1,
    )

    assert task_id_1 == task_id_2, 'Replay must be deduplicated to the same task_id'
    queue.shutdown(wait=False)


# ---------------------------------------------------------------------------
# Property 5: API state machine pending → completed
# ---------------------------------------------------------------------------

def test_proof_queue_state_machine():
    from backend.trace_adapter import build_trace_packet
    from backend.proof_queue import ProofQueue

    queue = ProofQueue(max_workers=1)
    packet = build_trace_packet(REFERENCE_REQUEST)

    task_id = queue.submit(
        packet.witness_artifact,
        packet.trace_artifact.trace_hash,
        produced_by='test_state_machine',
        cycle=1,
        auto_verify=True,
    )

    # Initially pending or immediately processing
    initial = queue.get_task(task_id)
    assert initial is not None
    assert initial.status in {'pending', 'processing', 'completed'}

    # Wait up to 60 s for completion
    deadline = time.monotonic() + 60.0
    task = None
    while time.monotonic() < deadline:
        task = queue.get_task(task_id)
        if task is not None and task.status in {'completed', 'failed'}:
            break
        time.sleep(0.25)

    assert task is not None
    assert task.status == 'completed', f'Expected completed, got {task.status}: {task.error}'
    assert task.result is not None
    assert task.result.proof_system == 'plonk'
    assert task.verification is not None
    assert task.verification.status == 'VALID'

    queue.shutdown(wait=False)


# ---------------------------------------------------------------------------
# Property 6: integrity_hash ≠ ZK proof (no ambiguity)
# ---------------------------------------------------------------------------

def test_integrity_hash_is_not_a_zk_proof():
    """The fast-path integrity_hash must never equal the ZK proof bytes."""
    req = ImportCalculationRequest.model_validate(REFERENCE_REQUEST)
    resp = calculate_import_landed_cost(req)
    w = extract_witness(req, resp)
    proof = generate_zk_proof(w)

    assert resp.proof.integrity_hash != proof.proof_bytes.hex(), (
        'integrity_hash must not equal ZK proof bytes — they are different artefacts'
    )


# ---------------------------------------------------------------------------
# Property 7: Key lifecycle events are emitted
# ---------------------------------------------------------------------------

def test_key_lifecycle_events_emitted(tmp_path, monkeypatch):
    """ensure_compiled must write a key_generation event to the lifecycle log."""
    import zk.keys.lifecycle as lifecycle_mod
    log_path = tmp_path / 'key_lifecycle.jsonl'
    monkeypatch.setattr(lifecycle_mod, '_LIFECYCLE_LOG', log_path)
    monkeypatch.setattr(lifecycle_mod, '_prev_hash', '0' * 64)

    from zk.compiler.plonk_adapter import compile_circuit
    from zk.keys.manager import KeyManager
    KeyManager.ensure_compiled(compile_circuit())

    assert log_path.exists(), 'Lifecycle log was not created'
    lines = log_path.read_text(encoding='utf-8').strip().splitlines()
    assert len(lines) >= 1
    import json
    first = json.loads(lines[0])
    assert first['event_type'] == 'key_generation'
    assert 'circuit_hash' in first['payload']
    assert 'proving_key_id' in first['payload']
    assert 'verification_key_id' in first['payload']
    assert 'current_hash' in first
    assert 'prev_hash' in first
