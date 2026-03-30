from __future__ import annotations

import pytest

from app.services.evidence_service import EvidenceService
from core.sample import REFERENCE_REQUEST
from tests.fakes import InMemoryEvidenceRepository


@pytest.mark.asyncio
async def test_verify_persisted_recomputes_valid_evidence() -> None:
    repository = InMemoryEvidenceRepository()
    service = EvidenceService(repository)

    persisted = await service.calculate_and_persist(REFERENCE_REQUEST)
    verified = await service.verify_persisted(REFERENCE_REQUEST)

    assert persisted.evidence.request.input_hash == verified.verification.recomputed_input_hash
    assert verified.verification.status == 'VALID'
    assert verified.audit_chain is not None
    assert verified.audit_chain.status == 'VALID'


@pytest.mark.asyncio
async def test_verify_persisted_detects_tampered_output() -> None:
    repository = InMemoryEvidenceRepository()
    service = EvidenceService(repository)

    persisted = await service.calculate_and_persist(REFERENCE_REQUEST)
    repository.tamper_result_landed_cost(persisted.proof.input_hash, '9999.99')

    verified = await service.verify_persisted(REFERENCE_REQUEST)
    assert verified.verification.status == 'INVALID'
