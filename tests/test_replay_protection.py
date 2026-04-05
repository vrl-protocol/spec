from __future__ import annotations

import pytest

from app.db.repository import DuplicateInputHashError
from app.services.evidence_service import EvidenceService
from core.sample import REFERENCE_REQUEST
from tests.fakes import InMemoryEvidenceRepository


@pytest.mark.asyncio
async def test_duplicate_input_hash_is_rejected_and_audited() -> None:
    repository = InMemoryEvidenceRepository()
    service = EvidenceService(repository)

    await service.calculate_and_persist(REFERENCE_REQUEST)

    with pytest.raises(DuplicateInputHashError):
        await service.calculate_and_persist(REFERENCE_REQUEST)

    audit_chain = await service.verify_audit_chain()
    assert repository.request_count == 1
    assert repository.result_count == 1
    assert repository.proof_count == 1
    assert repository.audit_count == 2
    assert audit_chain.status == 'VALID'
