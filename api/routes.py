from __future__ import annotations

import json
import os
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import ValidationError
from fastapi.responses import JSONResponse

from api.runtime import runtime
from app.db.repository import DuplicateInputHashError, PersistenceIntegrityError, RepositoryUnavailableError
from app.services.evidence_service import EvidenceService
from app.services.training_service import VerifiedTrainingService
from models.schemas import ImportCalculationRequest, PersistedVerificationRequest
from security.api_keys import api_key_store
from security.backpressure import BackpressureError, QueueDepthGuard
from security.guards import MAX_REQUEST_BYTES, SecurityViolation, enforce_payload_guards
from security.rate_limit import RateLimiter

router = APIRouter()
rate_limiter = RateLimiter(
    limit=int(os.getenv('VRL_API_RATE_LIMIT', '60')),
    window_seconds=int(os.getenv('VRL_API_RATE_LIMIT_WINDOW_SECONDS', '60')),
)
queue_guard = QueueDepthGuard(
    max_in_flight=int(os.getenv('VRL_MAX_IN_FLIGHT', '200')),
)


def _client_key(request: Request) -> str:
    client = request.client.host if request.client else 'unknown'
    return client


def _service_or_503(request: Request) -> EvidenceService:
    service = getattr(request.app.state, 'evidence_service', None)
    if service is None:
        raise HTTPException(status_code=503, detail='Database evidence repository is not configured')
    return service


def _training_service_or_503(request: Request) -> VerifiedTrainingService:
    service = getattr(request.app.state, 'training_service', None)
    if service is None:
        raise HTTPException(status_code=503, detail='Database training repository is not configured')
    return service


def _invalid_verification_response(reason: str) -> JSONResponse:
    return JSONResponse(content={'valid': False, 'reason': reason}, status_code=200)


def _require_api_key(x_api_key: str | None) -> None:
    """Enforce API key auth when keys are registered.

    When VRL_API_KEYS is empty (dev mode), all requests are allowed.
    In production (keys registered), requests without a valid X-Api-Key
    header are rejected with 401.
    """
    if not api_key_store.is_enabled():
        return
    if not x_api_key:
        raise HTTPException(status_code=401, detail="X-Api-Key header is required")
    record = api_key_store.authenticate(x_api_key)
    if record is None:
        raise HTTPException(status_code=401, detail="Invalid API key")


async def _load_json_payload(request: Request) -> dict[str, Any]:
    body = await request.body()
    if len(body) > MAX_REQUEST_BYTES:
        raise HTTPException(status_code=413, detail='Request body too large')
    if not body:
        return {}
    try:
        payload = json.loads(body.decode('utf-8'), parse_float=Decimal, parse_int=int)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail='Invalid JSON payload') from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail='JSON body must be an object')
    try:
        enforce_payload_guards(payload)
    except SecurityViolation as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return payload


@router.get('/healthz')
def healthz(request: Request) -> dict[str, Any]:
    return {
        'status': 'ok',
        'database_configured': getattr(request.app.state, 'evidence_service', None) is not None,
    }


@router.get('/status')
def status(request: Request) -> dict[str, Any]:
    dashboard = runtime.dashboard()
    dashboard['database_configured'] = getattr(request.app.state, 'evidence_service', None) is not None
    return dashboard


@router.get('/dashboard')
async def dashboard(request: Request) -> dict[str, Any]:
    dashboard = runtime.dashboard()
    service = getattr(request.app.state, 'evidence_service', None)
    dashboard['database_configured'] = service is not None
    if service is not None:
        dashboard['audit_chain'] = (await service.verify_audit_chain()).model_dump(mode='json')
    return dashboard


@router.get('/metrics')
def metrics(request: Request) -> dict:
    """Per-chain throughput, lock wait, error rates, backpressure stats."""
    from core.chain_metrics import chain_metrics
    cm = chain_metrics.snapshot()
    bp = queue_guard.snapshot()
    return {
        'chain_metrics': cm,
        'backpressure': bp,
        'api_keys': api_key_store.snapshot(),
    }


@router.get('/training/dataset')
async def training_dataset(
    request: Request,
    limit: int = 1000,
    x_api_key: str | None = Header(default=None),
) -> JSONResponse:
    _require_api_key(x_api_key)
    if limit < 1 or limit > 10000:
        raise HTTPException(status_code=400, detail='limit must be between 1 and 10000')
    try:
        export = await _training_service_or_503(request).export_dataset(limit=limit)
    except RepositoryUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail='Unable to export verified training dataset') from exc
    return JSONResponse(content=export.model_dump(mode='json'))


@router.get('/training/moat')
async def training_moat(
    request: Request,
    limit: int = 1000,
    x_api_key: str | None = Header(default=None),
) -> JSONResponse:
    _require_api_key(x_api_key)
    if limit < 1 or limit > 10000:
        raise HTTPException(status_code=400, detail='limit must be between 1 and 10000')
    try:
        metrics_payload = await _training_service_or_503(request).moat_metrics(limit=limit)
    except RepositoryUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail='Unable to compute moat metrics') from exc
    return JSONResponse(content=metrics_payload.model_dump(mode='json'))


@router.post('/calculate')
async def calculate(request: Request, x_api_key: str | None = Header(default=None)) -> JSONResponse:
    """Calculate import landed cost.

    Evidence persistence is mandatory. Requests are rejected when the
    evidence repository is not configured.
    """
    _require_api_key(x_api_key)
    rate_result = rate_limiter.allow(_client_key(request))
    if not rate_result.allowed:
        raise HTTPException(status_code=429, detail='Rate limit exceeded')
    payload = await _load_json_payload(request)
    try:
        async with queue_guard.guarded():
            model = ImportCalculationRequest.model_validate(payload)
            service = _service_or_503(request)
            persisted = await service.calculate_and_persist(model.model_dump(mode='python'))
            runtime.record_response(
                persisted,
                audit_hash=persisted.evidence.audit_log.current_hash if persisted.evidence.audit_log else None,
            )
            body = persisted.model_dump(mode='json')
            body['integrity_hash'] = persisted.integrity.integrity_hash
            body['proof_status'] = 'persisted'
            return JSONResponse(content=body)
    except HTTPException:
        raise
    except BackpressureError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except DuplicateInputHashError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RepositoryUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SecurityViolation as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail='Input validation failed') from exc
    except PersistenceIntegrityError as exc:
        raise HTTPException(status_code=500, detail='Persistence integrity check failed') from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail='Unable to calculate landed cost') from exc


@router.post('/prove')
async def prove(request: Request, x_api_key: str | None = Header(default=None)) -> JSONResponse:
    """Enqueue a PLONK proof job for the given import request.

    Returns a task_id immediately.  Poll GET /proof/{task_id} for status.
    The ZK pipeline consumes the EXACT same trace produced by the engine —
    no recomputation, no mutation.
    """
    _require_api_key(x_api_key)
    rate_result = rate_limiter.allow(_client_key(request))
    if not rate_result.allowed:
        raise HTTPException(status_code=429, detail='Rate limit exceeded')
    payload = await _load_json_payload(request)
    try:
        async with queue_guard.guarded():
            _service_or_503(request)
            from backend.trace_adapter import build_trace_packet
            from backend.proof_queue import proof_queue
            packet = build_trace_packet(payload)
            task_id = proof_queue.submit(
                packet.witness_artifact,
                packet.trace_artifact.trace_hash,
                produced_by='api_prove',
                cycle=1,
                auto_verify=True,
            )
    except HTTPException:
        raise
    except BackpressureError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RepositoryUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SecurityViolation as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail='Input validation failed') from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail='Unable to enqueue proof') from exc
    return JSONResponse(content={
        'task_id': task_id,
        'status': 'pending',
        'trace_hash': packet.trace_artifact.trace_hash,
        'circuit_hash': packet.witness_artifact.artifact_id,
    })


@router.get('/proof/{task_id}')
def get_proof(task_id: str, request: Request, x_api_key: str | None = Header(default=None)) -> JSONResponse:
    """Poll a proof job by task ID.

    Returns:
      status=pending/processing  — job in flight
      status=completed           — zk_proof + verification included
      status=failed              — error message included
    """
    _require_api_key(x_api_key)
    from backend.proof_queue import proof_queue
    task = proof_queue.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail='Proof task not found')
    body: dict[str, Any] = {'task_id': task_id, 'status': task.status}
    if task.status == 'completed' and task.result is not None:
        body['zk_proof'] = task.result.model_dump(mode='json')
        if task.verification is not None:
            body['verification'] = task.verification.model_dump(mode='json')
    elif task.status == 'failed':
        body['error'] = task.error
    return JSONResponse(content=body)


@router.post('/verify')
async def verify(request: Request, x_api_key: str | None = Header(default=None)) -> JSONResponse:
    _require_api_key(x_api_key)
    rate_result = rate_limiter.allow(_client_key(request))
    if not rate_result.allowed:
        raise HTTPException(status_code=429, detail='Rate limit exceeded')
    payload = await _load_json_payload(request)
    try:
        model = PersistedVerificationRequest.model_validate(payload)
        result = await _service_or_503(request).verify_persisted(model.request.model_dump(mode='python'))
    except RepositoryUnavailableError as exc:
        return _invalid_verification_response(str(exc))
    except SecurityViolation as exc:
        return _invalid_verification_response(str(exc))
    except ValidationError as exc:
        return _invalid_verification_response(f'Input validation failed: {exc}')
    except Exception as exc:
        return _invalid_verification_response(f'Unable to verify persisted evidence: {exc}')
    return JSONResponse(content=result.model_dump(mode='json'))


@router.post('/run')
async def run(request: Request, x_api_key: str | None = Header(default=None)) -> JSONResponse:
    _require_api_key(x_api_key)
    rate_result = rate_limiter.allow(_client_key(request))
    if not rate_result.allowed:
        raise HTTPException(status_code=429, detail='Rate limit exceeded')
    payload = await _load_json_payload(request)
    if not payload:
        raise HTTPException(status_code=400, detail='Explicit input payload is required for deterministic execution')
    request_payload = payload
    try:
        async with queue_guard.guarded():
            persisted = await _service_or_503(request).calculate_and_persist(request_payload)
        runtime.record_response(persisted, audit_hash=persisted.evidence.audit_log.current_hash if persisted.evidence.audit_log else None)
    except BackpressureError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except DuplicateInputHashError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RepositoryUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SecurityViolation as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail='Input validation failed') from exc
    except PersistenceIntegrityError as exc:
        raise HTTPException(status_code=500, detail='Persistence integrity check failed') from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail='Unable to run deterministic calculation') from exc
    return JSONResponse(content=persisted.model_dump(mode='json'))


@router.post('/start')
def start(request: Request) -> dict[str, Any]:
    _service_or_503(request)
    snapshot = runtime.start()
    return {'status': 'started', 'runtime': snapshot.__dict__}


@router.post('/stop')
def stop() -> dict[str, Any]:
    snapshot = runtime.stop()
    return {'status': 'stopped', 'runtime': snapshot.__dict__}



