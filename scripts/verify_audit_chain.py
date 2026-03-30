from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.connection import DatabaseSettings, close_pool, create_pool  # noqa: E402
from app.db.repository import PostgresEvidenceRepository, RepositoryUnavailableError  # noqa: E402
from app.services.evidence_service import EvidenceService  # noqa: E402


async def main() -> int:
    settings = DatabaseSettings.from_env()
    if settings is None:
        raise RepositoryUnavailableError('VRL_DATABASE_URL is required to verify the audit chain')
    pool = await create_pool(settings)
    try:
        repository = PostgresEvidenceRepository(
            pool,
            statement_timeout_ms=settings.statement_timeout_ms,
            lock_timeout_ms=settings.lock_timeout_ms,
            connect_timeout_seconds=settings.connect_timeout_seconds,
        )
        service = EvidenceService(repository)
        result = await service.verify_audit_chain()
        print(result.model_dump_json(indent=2))
        return 0 if result.status == 'VALID' else 1
    finally:
        await close_pool(pool)


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
