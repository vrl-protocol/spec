from __future__ import annotations

import asyncio

import pytest

from app.services.evidence_service import EvidenceService
from core.sample import REFERENCE_REQUEST
from tests.fakes import InMemoryEvidenceRepository


@pytest.mark.asyncio
async def test_concurrent_writes_preserve_audit_chain_integrity() -> None:
    repository = InMemoryEvidenceRepository()
    service = EvidenceService(repository)

    payloads = []
    for index in range(5):
        payload = dict(REFERENCE_REQUEST)
        payload['quantity'] = index + 1
        payloads.append(payload)

    results = await asyncio.gather(*(service.calculate_and_persist(payload) for payload in payloads))
    audit_chain = await service.verify_audit_chain()

    assert len(results) == 5
    assert repository.request_count == 5
    assert repository.audit_count == 5
    assert audit_chain.status == 'VALID'
