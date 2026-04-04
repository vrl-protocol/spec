from __future__ import annotations

import pytest

from app.services.evidence_service import EvidenceService
from backend.verified_dataset import build_verified_training_record
from backend.trace_adapter import build_trace_packet
from core.sample import REFERENCE_REQUEST
from zk.provers.plonk_prover import build_plonk_proof
from tests.fakes import InMemoryEvidenceRepository


@pytest.mark.asyncio
async def test_calculate_and_persist_creates_evidence_records() -> None:
    repository = InMemoryEvidenceRepository()
    service = EvidenceService(repository)

    persisted = await service.calculate_and_persist(REFERENCE_REQUEST)
    stored = await repository.fetch_by_input_hash(persisted.integrity.input_hash)

    assert stored is not None
    assert stored.request.input_hash == persisted.integrity.input_hash
    assert stored.result.output_hash == persisted.integrity.output_hash
    assert stored.proof.integrity_hash == persisted.integrity.integrity_hash
    assert stored.proof.final_proof
    assert stored.proof.proof_system == 'plonk'
    assert stored.proof.proof_verified is True
    assert stored.proof.proof_bundle['trace_hash'] == persisted.integrity.trace_hash
    assert stored.audit_log is not None
    assert repository.request_count == 1
    assert repository.result_count == 1
    assert repository.proof_count == 1
    assert repository.audit_count == 1


@pytest.mark.asyncio
async def test_verified_training_record_can_be_built_from_persisted_evidence() -> None:
    repository = InMemoryEvidenceRepository()
    service = EvidenceService(repository)

    persisted = await service.calculate_and_persist(REFERENCE_REQUEST)
    packet = build_trace_packet(REFERENCE_REQUEST)
    zk_proof = build_plonk_proof(packet.witness_artifact, packet.trace_artifact.trace_hash)
    record = build_verified_training_record(
        persisted,
        zk_proof=zk_proof,
        witness_hash=packet.witness_artifact.witness_hash,
        verification_key_hash=persisted.evidence.proof.verification_key_hash,
        proof_bundle=persisted.evidence.proof.proof_bundle,
    )

    assert record.verification_status == 'VERIFIED'
    assert record.input_hash == persisted.integrity.input_hash
    assert record.trace_hash == persisted.integrity.trace_hash
    assert record.final_proof == zk_proof.final_proof
