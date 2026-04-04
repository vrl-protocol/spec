from __future__ import annotations

import importlib

from fastapi.testclient import TestClient

from app.services.evidence_service import EvidenceService
from backend.proof_export import export_proof_bundle, verify_proof_bundle
from core.sample import REFERENCE_REQUEST
from tests.fakes import InMemoryEvidenceRepository


def test_verify_proof_bundle_returns_invalid_for_malformed_proof_payload() -> None:
    bundle = export_proof_bundle(REFERENCE_REQUEST)
    bundle['proof']['metadata']['circuit_hash'] = '0' * 64

    result = verify_proof_bundle(bundle)

    assert result['valid'] is False
    assert 'bundle verification failed' in result['reason']


def test_app_requires_database_in_production(monkeypatch) -> None:
    monkeypatch.setenv('VRL_ENV', 'production')
    monkeypatch.delenv('VRL_DATABASE_URL', raising=False)

    import app.main as app_main

    importlib.reload(app_main)

    async def _enter_lifespan() -> None:
        async with app_main.lifespan(app_main.app):
            pass

    import asyncio

    try:
        try:
            asyncio.run(_enter_lifespan())
        except RuntimeError as exc:
            assert 'VRL_DATABASE_URL is required' in str(exc)
        else:
            raise AssertionError('Expected production startup to require a database')
    finally:
        monkeypatch.delenv('VRL_ENV', raising=False)
        importlib.reload(app_main)


def test_calculate_requires_database_configuration() -> None:
    from app.main import app

    with TestClient(app) as client:
        response = client.post('/calculate', json={
            'hs_code': '8507600000',
            'country_of_origin': 'CN',
            'customs_value': '1200.00',
            'freight': '150.00',
            'insurance': '25.00',
            'quantity': 2,
            'shipping_mode': 'ocean',
        })

    assert response.status_code == 503


def test_verify_returns_invalid_not_500_for_missing_database() -> None:
    from app.main import app

    with TestClient(app) as client:
        response = client.post('/verify', json={'request': {
            'hs_code': '8507600000',
            'country_of_origin': 'CN',
            'customs_value': '1200.00',
            'freight': '150.00',
            'insurance': '25.00',
            'quantity': 2,
            'shipping_mode': 'ocean',
        }})

    assert response.status_code == 200
    assert response.json()['valid'] is False


def test_verify_returns_invalid_not_500_for_malformed_stored_response() -> None:
    from app.main import app

    repository = InMemoryEvidenceRepository()
    service = EvidenceService(repository)

    import asyncio
    persisted = asyncio.run(service.calculate_and_persist(REFERENCE_REQUEST))
    repository.tamper_result_landed_cost(persisted.integrity.input_hash, '9999.99')
    request_record = repository._state.requests_by_input_hash[persisted.integrity.input_hash]
    result_record = repository._state.results_by_request_id[request_record.id]
    repository._state.results_by_request_id[request_record.id] = result_record.model_copy(
        update={'raw_output': {'unexpected': 'shape'}},
        deep=True,
    )

    app.state.evidence_service = service
    try:
        with TestClient(app) as client:
            response = client.post('/verify', json={'request': {
                'hs_code': '8507600000',
                'country_of_origin': 'CN',
                'customs_value': '1200.00',
                'freight': '150.00',
                'insurance': '25.00',
                'quantity': 2,
                'shipping_mode': 'ocean',
            }})
    finally:
        app.state.evidence_service = None

    assert response.status_code == 200
    assert response.json()['valid'] is False


def test_verify_returns_invalid_for_legacy_record() -> None:
    repository = InMemoryEvidenceRepository()
    service = EvidenceService(repository)

    import asyncio
    persisted = asyncio.run(service.calculate_and_persist(REFERENCE_REQUEST))
    repository._state.proofs_by_request_id[persisted.evidence.proof.request_id] = persisted.evidence.proof.model_copy(
        update={'proof_system': 'legacy'},
        deep=True,
    )

    verified = asyncio.run(service.verify_persisted(REFERENCE_REQUEST))

    assert verified.verification.status == 'INVALID'
    assert verified.verification.reason == 'legacy record'
