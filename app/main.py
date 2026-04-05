from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routes import router
from api.runtime import runtime
from app.db.connection import DatabaseSettings, close_pool, create_pool
from app.db.repository import PostgresEvidenceRepository
from app.services.evidence_service import EvidenceService
from app.services.training_service import VerifiedTrainingService


@asynccontextmanager
async def lifespan(app: FastAPI):
    runtime.stop()
    settings = DatabaseSettings.from_env()
    runtime_mode = os.getenv('VRL_ENV', 'development').strip().lower()
    pool = None
    evidence_service = None
    if runtime_mode == 'production' and settings is None:
        raise RuntimeError('VRL_DATABASE_URL is required when VRL_ENV=production')
    if settings is not None:
        pool = await create_pool(settings)
        repository = PostgresEvidenceRepository(
            pool,
            statement_timeout_ms=settings.statement_timeout_ms,
            lock_timeout_ms=settings.lock_timeout_ms,
            connect_timeout_seconds=settings.connect_timeout_seconds,
        )
        evidence_service = EvidenceService(repository)
        training_service = VerifiedTrainingService(repository)
    else:
        training_service = VerifiedTrainingService(None)
    app.state.db_pool = pool
    app.state.evidence_service = evidence_service
    app.state.training_service = training_service
    try:
        yield
    finally:
        runtime.stop()
        await close_pool(pool)


app = FastAPI(title='Verifiable Reality Layer', version='1.1.0', lifespan=lifespan)
app.include_router(router)
