from __future__ import annotations

import pytest

from app.services.evidence_service import EvidenceService
from core.sample import REFERENCE_REQUEST
from tests.fakes import InMemoryEvidenceRepository


@pytest.mark.asyncio
async def test_calculate_and_persist_creates_evidence_records() -> None:
    repository = InMemoryEvidenceRepository()
    service = EvidenceService(repository)

    persisted = await service.calculate_and_persist(REFERENCE_REQUEST)
    stored = await repository.fetch_by_input_hash(persisted.proof.input_hash)

    assert stored is not None
    assert stored.request.input_hash == persisted.proof.input_hash
    assert stored.result.output_hash == persisted.proof.output_hash
    assert stored.proof.integrity_hash == persisted.proof.integrity_hash
    assert stored.audit_log is not None
    assert repository.request_count == 1
    assert repository.result_count == 1
    assert repository.proof_count == 1
    assert repository.audit_count == 1
