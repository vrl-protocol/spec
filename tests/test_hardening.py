from __future__ import annotations

import asyncio
import hashlib
import ssl

import pytest

from app.db.connection import DatabaseSettings, TLSEnforcementError, _ssl_context
from core.audit_chain import AUDIT_CHAIN_PARTITIONS, chain_id_for_input
from core.chain_checkpoint import compute_checkpoint_hash
from core.chain_metrics import ChainMetrics
from core.engine import calculate_import_landed_cost
from core.sample import REFERENCE_REQUEST
from core.zk_interface import extract_witness, generate_zk_proof, verify_zk_proof
from models.schemas import ImportCalculationRequest
from security.api_keys import ApiKeyStore
from security.backpressure import BackpressureError, QueueDepthGuard
from utils.canonical import canonical_json


# --- Task 1: full-hash modulo ---


def test_chain_id_full_hash():
    h1 = "abcdef1234567890" + "0" * 48
    h2 = "abcdef1234567890" + "f" * 48
    assert chain_id_for_input(h1) != chain_id_for_input(h2)


def test_chain_id_distribution():
    counts = [0] * AUDIT_CHAIN_PARTITIONS
    for i in range(10_000):
        h = hashlib.sha256(str(i).encode()).hexdigest()
        counts[chain_id_for_input(h)] += 1
    avg = 10_000 / AUDIT_CHAIN_PARTITIONS
    assert max(counts) < avg * 4
    assert min(counts) > avg / 4


# --- Task 1: per-chain metrics ---


def test_metrics_counters():
    m = ChainMetrics()
    m.record_request(0)
    m.record_request(0)
    m.record_success(0)
    m.record_duplicate(1)
    m.record_error(2)
    s = m.snapshot()
    assert s["total_requests"] == 2
    assert s["chains"][0]["successes"] == 1
    assert s["chains"][1]["duplicates"] == 1
    assert s["chains"][2]["errors"] == 1


def test_metrics_hotspot():
    m = ChainMetrics()
    for _ in range(100):
        m.record_request(0)
    assert 0 in m.chains_above_threshold(hotspot_factor=2.0)


def test_metrics_no_hotspot_uniform():
    m = ChainMetrics()
    for i in range(AUDIT_CHAIN_PARTITIONS):
        m.record_request(i)
    assert m.chains_above_threshold() == []


# --- Task 2: chain checkpointing ---


def test_checkpoint_deterministic():
    h = compute_checkpoint_hash(
        chain_id=0, segment_index=0, last_record_id=999, last_current_hash="a" * 64
    )
    h2 = compute_checkpoint_hash(
        chain_id=0, segment_index=0, last_record_id=999, last_current_hash="a" * 64
    )
    assert h == h2 and len(h) == 64


def test_checkpoint_differs_chain():
    h1 = compute_checkpoint_hash(
        chain_id=0, segment_index=0, last_record_id=1, last_current_hash="a" * 64
    )
    h2 = compute_checkpoint_hash(
        chain_id=1, segment_index=0, last_record_id=1, last_current_hash="a" * 64
    )
    assert h1 != h2


def test_checkpoint_differs_segment():
    h1 = compute_checkpoint_hash(
        chain_id=0, segment_index=0, last_record_id=1, last_current_hash="a" * 64
    )
    h2 = compute_checkpoint_hash(
        chain_id=0, segment_index=1, last_record_id=1, last_current_hash="a" * 64
    )
    assert h1 != h2


# --- Task 3: ZK interface ---


def test_zk_witness():
    req = ImportCalculationRequest.model_validate(REFERENCE_REQUEST)
    resp = calculate_import_landed_cost(req)
    w = extract_witness(req, resp)
    assert w.input_hash == resp.proof.input_hash
    assert w.output_hash == resp.proof.output_hash
    assert "hs_code" in w.public_inputs
    assert "landed_cost" in w.public_inputs


def test_zk_plonk_proof_is_valid():
    """Real PLONK proof must verify and be distinct from the integrity_hash."""
    req = ImportCalculationRequest.model_validate(REFERENCE_REQUEST)
    resp = calculate_import_landed_cost(req)
    w = extract_witness(req, resp)
    proof = generate_zk_proof(w)
    # proof_bytes must be non-empty and even-length hex
    assert len(proof.proof_bytes) > 0
    assert len(proof.proof_bytes.hex()) % 2 == 0
    # PLONK proof must NOT equal the integrity_hash (different systems, different values)
    assert proof.proof_bytes.hex() != resp.proof.integrity_hash
    # verification_key_id must indicate PLONK backend, not the old SHA256 stub
    assert proof.verification_key_id != 'sha256-stub-v1'
    # deterministic re-proof must verify
    assert verify_zk_proof(proof, w)


# --- Task 4: TLS enforcement ---


def test_tls_required_default():
    s = DatabaseSettings(url="postgresql://x:y@localhost/z", require_tls=True)
    ctx = _ssl_context(s)
    assert isinstance(ctx, ssl.SSLContext)
    assert ctx.verify_mode == ssl.CERT_REQUIRED


def test_tls_disabled_raises():
    s = DatabaseSettings(url="postgresql://x:y@localhost/z", require_tls=False)
    with pytest.raises(TLSEnforcementError):
        _ssl_context(s)


def test_tls_dev_override(monkeypatch):
    monkeypatch.setenv("VRL_ALLOW_PLAINTEXT", "true")
    s = DatabaseSettings(url="postgresql://x:y@localhost/z", require_tls=False)
    assert _ssl_context(s) is None


# --- Task 5: input normalization ---


def test_canonical_nfc():
    j1 = canonical_json({"k": "cafe\u0301"})
    j2 = canonical_json({"k": "caf\xe9"})
    assert j1 == j2


def test_canonical_ascii():
    j = canonical_json({"k": "\xe9"})
    assert "\xe9" not in j


def test_canonical_rejects_float():
    with pytest.raises(TypeError):
        canonical_json({"v": 1.5})


def test_canonical_bool():
    import json
    assert json.loads(canonical_json({"f": True}))["f"] is True


# --- Task 6: backpressure ---


def test_backpressure_limit():
    g = QueueDepthGuard(max_in_flight=2)
    g.acquire()
    g.acquire()
    with pytest.raises(BackpressureError):
        g.acquire()
    assert g.rejected_total == 1


def test_backpressure_release():
    g = QueueDepthGuard(max_in_flight=1)
    g.acquire()
    with pytest.raises(BackpressureError):
        g.acquire()
    g.release()
    g.acquire()
    assert g.current_depth == 1


def test_backpressure_async():
    async def _r():
        g = QueueDepthGuard(max_in_flight=3)
        async with g.guarded():
            assert g.current_depth == 1
        assert g.current_depth == 0

    asyncio.run(_r())


# --- Task 8: API key authentication ---


def _store():
    from threading import Lock

    s = object.__new__(ApiKeyStore)
    s._lock = Lock()
    s._keys = {}
    return s


def test_apikey_open_mode():
    assert not _store().is_enabled()


def test_apikey_register_auth():
    s = _store()
    s.register("svc-a", "sk_test")
    rec = s.authenticate("sk_test")
    assert rec.label == "svc-a"
    assert rec.requests_total == 1


def test_apikey_invalid():
    s = _store()
    s.register("svc-a", "sk_test")
    assert s.authenticate("wrong") is None


def test_apikey_tracking():
    s = _store()
    s.register("svc", "k")
    for _ in range(5):
        s.authenticate("k")
    assert s.snapshot()[0]["requests_total"] == 5
