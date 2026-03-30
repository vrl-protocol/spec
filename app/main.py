from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routes import router
from api.runtime import runtime
from app.db.connection import DatabaseSettings, close_pool, create_pool
from app.db.repository import PostgresEvidenceRepository
from app.services.evidence_service import EvidenceService


@asynccontextmanager
async def lifespan(app: FastAPI):
    runtime.stop()
    settings = DatabaseSettings.from_env()
    pool = None
    evidence_service = None
    if settings is not None:
        pool = await create_pool(settings)
        repository = PostgresEvidenceRepository(
            pool,
            statement_timeout_ms=settings.statement_timeout_ms,
            lock_timeout_ms=settings.lock_timeout_ms,
            connect_timeout_seconds=settings.connect_timeout_seconds,
        )
        evidence_service = EvidenceService(repository)
    app.state.db_pool = pool
    app.state.evidence_service = evidence_service
    try:
        yield
    finally:
        runtime.stop()
        await close_pool(pool)


app = FastAPI(title='Verifiable Reality Layer', version='1.1.0', lifespan=lifespan)
app.include_router(router)
