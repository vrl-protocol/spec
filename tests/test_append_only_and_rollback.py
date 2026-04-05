from __future__ import annotations

from pathlib import Path

import pytest

from app.db.repository import AppendOnlyViolationError
from app.services.evidence_service import EvidenceService
from core.sample import REFERENCE_REQUEST
from tests.fakes import InMemoryEvidenceRepository, InjectedFailure

MIGRATION_PATH = Path(r'C:\Users\13173\OneDrive\Documents\verifiable-reality-layer\migrations\001_init.sql')


@pytest.mark.asyncio
async def test_transaction_rolls_back_on_partial_failure() -> None:
    repository = InMemoryEvidenceRepository()
    repository.fail_on = 'insert_result'
    service = EvidenceService(repository)

    with pytest.raises(InjectedFailure):
        await service.calculate_and_persist(REFERENCE_REQUEST)

    assert repository.request_count == 0
    assert repository.result_count == 0
    assert repository.proof_count == 0
    assert repository.audit_count == 1


def test_append_only_update_and_delete_are_rejected() -> None:
    repository = InMemoryEvidenceRepository()

    with pytest.raises(AppendOnlyViolationError):
        repository.attempt_update_request()

    with pytest.raises(AppendOnlyViolationError):
        repository.attempt_delete_request()


def test_migration_contains_append_only_guards() -> None:
    sql = MIGRATION_PATH.read_text(encoding='utf-8')
    assert 'BEFORE UPDATE OR DELETE ON requests' in sql
    assert 'BEFORE UPDATE OR DELETE ON results' in sql
    assert 'BEFORE UPDATE OR DELETE ON proofs' in sql
    assert 'BEFORE UPDATE OR DELETE ON audit_log' in sql
    assert 'REVOKE UPDATE, DELETE ON requests, results, proofs, audit_log' in sql
