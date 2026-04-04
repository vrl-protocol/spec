from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.evidence_service import EvidenceService
from app.services.training_service import VerifiedTrainingService
from core.sample import REFERENCE_REQUEST
from tests.fakes import InMemoryEvidenceRepository


@pytest.mark.asyncio
async def test_verified_dataset_export_only_contains_proof_verified_records() -> None:
    repository = InMemoryEvidenceRepository()
    evidence_service = EvidenceService(repository)
    training_service = VerifiedTrainingService(repository)

    first = await evidence_service.calculate_and_persist(REFERENCE_REQUEST)
    second_request = dict(REFERENCE_REQUEST)
    second_request['customs_value'] = Decimal('1300.00')
    second = await evidence_service.calculate_and_persist(second_request)
    repository._state.proofs_by_request_id[second.evidence.proof.request_id] = second.evidence.proof.model_copy(
        update={'proof_verified': False},
        deep=True,
    )

    export = await training_service.export_dataset(limit=10)

    assert export.total_candidates == 1
    assert export.exportable_records == 1
    assert export.skipped_records == 0
    assert len(export.records) == 1
    assert export.records[0].input_hash == first.integrity.input_hash


@pytest.mark.asyncio
async def test_moat_metrics_summarize_verified_training_corpus() -> None:
    repository = InMemoryEvidenceRepository()
    evidence_service = EvidenceService(repository)
    training_service = VerifiedTrainingService(repository)

    await evidence_service.calculate_and_persist(REFERENCE_REQUEST)
    second_request = dict(REFERENCE_REQUEST)
    second_request['customs_value'] = Decimal('1300.00')
    second_request['country_of_origin'] = 'MX'
    await evidence_service.calculate_and_persist(second_request)

    metrics = await training_service.moat_metrics(limit=10)

    assert metrics.total_candidates == 2
    assert metrics.exportable_records == 2
    assert metrics.skipped_records == 0
    assert metrics.unique_input_hashes == 2
    assert metrics.unique_trace_hashes == 2
    assert metrics.unique_verification_keys == 1
    assert metrics.unique_origin_countries == 2
    assert metrics.unique_hs_codes == 1
    assert metrics.proof_systems == ['plonk']
    assert metrics.exportability_ratio == 1.0


@pytest.mark.asyncio
async def test_legacy_records_do_not_enter_training_dataset() -> None:
    repository = InMemoryEvidenceRepository()
    evidence_service = EvidenceService(repository)
    training_service = VerifiedTrainingService(repository)

    persisted = await evidence_service.calculate_and_persist(REFERENCE_REQUEST)
    repository._state.proofs_by_request_id[persisted.evidence.proof.request_id] = persisted.evidence.proof.model_copy(
        update={'proof_system': 'legacy'},
        deep=True,
    )

    export = await training_service.export_dataset(limit=10)

    assert export.exportable_records == 0
    assert export.records == []
