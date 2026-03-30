from __future__ import annotations

import pytest

from app.services.evidence_service import EvidenceService
from core.sample import REFERENCE_REQUEST
from tests.fakes import InMemoryEvidenceRepository


@pytest.mark.asyncio
async def test_audit_chain_detects_manual_tampering() -> None:
    repository = InMemoryEvidenceRepository()
    service = EvidenceService(repository)

    payload_one = dict(REFERENCE_REQUEST)
    payload_two = dict(REFERENCE_REQUEST)
    payload_two['quantity'] = 3

    await service.calculate_and_persist(payload_one)
    await service.calculate_and_persist(payload_two)

    verified_before = await service.verify_audit_chain()
    assert verified_before.status == 'VALID'

    repository.tamper_audit_hash(0, '0' * 64)
    verified_after = await service.verify_audit_chain()
    assert verified_after.status == 'INVALID'
