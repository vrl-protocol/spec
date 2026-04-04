from __future__ import annotations

from typing import Protocol

import asyncpg

from core.audit_chain import ZERO_HASH
from models.schemas import AuditEventRecord, PersistedEvidenceBundle, ProofRecord, RequestRecord, ResultRecord

# ---------------------------------------------------------------------------
# Per-chain advisory lock key derivation
# ---------------------------------------------------------------------------
# The single AUDIT_CHAIN_LOCK_KEY = 4_283_911 has been replaced with 64
# independent per-chain lock keys.  Each chain occupies its own advisory
# lock slot, reducing serialization contention ~64× under a uniform input
# hash distribution.
#
# Lock key = AUDIT_CHAIN_LOCK_BASE + chain_id  (chain_id: 0 … 63)
# The base is chosen to be far from any other advisory lock keys used in
# the application.
AUDIT_CHAIN_LOCK_BASE = 4_283_911_000


def chain_id_to_lock_key(chain_id: int) -> int:
    return AUDIT_CHAIN_LOCK_BASE + chain_id


# ---------------------------------------------------------------------------
# SQL constants
# ---------------------------------------------------------------------------

# Batch insert: request + result + proof in one round-trip using a CTE.
# The FK constraint results.request_id → requests.id is satisfied because
# PostgreSQL materialises the req CTE before executing res and prf.
BATCH_INSERT_RECORDS_SQL = """
WITH
  req AS (
    INSERT INTO requests (id, input_hash, raw_input, created_at)
    VALUES ($1, $2, $3, $4)
    RETURNING id
  ),
  res AS (
    INSERT INTO results (id, request_id, output_hash, raw_output, created_at)
    SELECT $5, req.id, $6, $7, $8 FROM req
    RETURNING id
  ),
  prf AS (
    INSERT INTO proofs (
      id,
      request_id,
      trace_hash,
      final_proof,
      integrity_hash,
      proof_system,
      circuit_hash,
      verification_key_hash,
      proof_bundle,
      proof_verified,
      created_at
    )
    SELECT $9, req.id, $10, $11, $12, $13, $14, $15, $16, $17, $18 FROM req
    RETURNING id
  )
SELECT 'ok'
"""

INSERT_AUDIT_SQL = """
INSERT INTO audit_log (chain_id, event_type, reference_id, event_payload, prev_hash, current_hash, created_at)
VALUES ($1, $2, $3, $4, $5, $6, $7)
RETURNING id
"""

# Lightweight duplicate check — index-only scan on requests_input_hash_unique.
# Replaces the expensive full JOIN bundle fetch used previously for duplicate
# detection inside the transaction.
CHECK_DUPLICATE_SQL = """
SELECT 1 FROM requests WHERE input_hash = $1
"""

# Per-chain latest hash: uses the new (chain_id, id) composite index.
FETCH_LATEST_AUDIT_HASH_FOR_CHAIN_SQL = """
SELECT current_hash
FROM audit_log
WHERE chain_id = $1
ORDER BY id DESC
LIMIT 1
"""

# Full bundle fetch (used by verify path outside the write transaction).
FETCH_BUNDLE_SQL = """
SELECT
    r.id AS request_id,
    r.input_hash,
    r.raw_input,
    r.created_at AS request_created_at,
    s.id AS result_id,
    s.request_id AS result_request_id,
    s.output_hash,
    s.raw_output,
    s.created_at AS result_created_at,
    p.id AS proof_id,
    p.request_id AS proof_request_id,
    p.trace_hash,
    p.final_proof,
    p.integrity_hash,
    p.proof_system,
    p.circuit_hash,
    p.verification_key_hash,
    p.proof_bundle,
    p.proof_verified,
    p.created_at AS proof_created_at,
    a.id AS audit_id,
    a.chain_id AS audit_chain_id,
    a.event_type AS audit_event_type,
    a.reference_id AS audit_reference_id,
    a.event_payload AS audit_event_payload,
    a.prev_hash AS audit_prev_hash,
    a.current_hash AS audit_current_hash,
    a.created_at AS audit_created_at
FROM requests r
JOIN results s ON s.request_id = r.id
JOIN proofs p ON p.request_id = r.id
LEFT JOIN LATERAL (
    SELECT id, chain_id, event_type, reference_id, event_payload, prev_hash, current_hash, created_at
    FROM audit_log
    WHERE reference_id = r.id
    ORDER BY id DESC
    LIMIT 1
) a ON TRUE
WHERE r.input_hash = $1
"""

# All audit records ordered so that per-chain sequences are contiguous.
# verify_audit_chain() groups by chain_id then validates each run in order.
FETCH_AUDIT_CHAIN_SQL = """
SELECT id, chain_id, event_type, reference_id, event_payload, prev_hash, current_hash, created_at
FROM audit_log
ORDER BY chain_id ASC, id ASC
"""

FETCH_TRAINING_CANDIDATES_SQL = """
SELECT
    r.id AS request_id,
    r.input_hash,
    r.raw_input,
    r.created_at AS request_created_at,
    s.id AS result_id,
    s.request_id AS result_request_id,
    s.output_hash,
    s.raw_output,
    s.created_at AS result_created_at,
    p.id AS proof_id,
    p.request_id AS proof_request_id,
    p.trace_hash,
    p.final_proof,
    p.integrity_hash,
    p.proof_system,
    p.circuit_hash,
    p.verification_key_hash,
    p.proof_bundle,
    p.proof_verified,
    p.created_at AS proof_created_at,
    a.id AS audit_id,
    a.chain_id AS audit_chain_id,
    a.event_type AS audit_event_type,
    a.reference_id AS audit_reference_id,
    a.event_payload AS audit_event_payload,
    a.prev_hash AS audit_prev_hash,
    a.current_hash AS audit_current_hash,
    a.created_at AS audit_created_at
FROM requests r
JOIN results s ON s.request_id = r.id
JOIN proofs p ON p.request_id = r.id
LEFT JOIN LATERAL (
    SELECT id, chain_id, event_type, reference_id, event_payload, prev_hash, current_hash, created_at
    FROM audit_log
    WHERE reference_id = r.id
    ORDER BY id DESC
    LIMIT 1
) a ON TRUE
WHERE p.proof_verified = TRUE
  AND p.proof_system = 'plonk'
ORDER BY p.created_at ASC, p.id ASC
LIMIT $1
"""

LOCK_AUDIT_CHAIN_SQL = "SELECT pg_advisory_xact_lock($1)"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class RepositoryError(RuntimeError):
    pass


class DuplicateInputHashError(RepositoryError):
    pass


class AppendOnlyViolationError(RepositoryError):
    pass


class PersistenceIntegrityError(RepositoryError):
    pass


class RepositoryUnavailableError(RepositoryError):
    pass


class RepositoryStateError(RepositoryError):
    pass


# ---------------------------------------------------------------------------
# Protocols
# ---------------------------------------------------------------------------

class RepositorySessionProtocol(Protocol):
    async def acquire_audit_chain_lock(self, chain_id: int) -> None: ...
    async def fetch_latest_audit_hash_for_chain(self, chain_id: int) -> str: ...
    async def check_duplicate(self, input_hash: str) -> bool: ...
    async def insert_records_batch(self, request: RequestRecord, result: ResultRecord, proof: ProofRecord) -> None: ...
    async def insert_audit_event(self, record: AuditEventRecord) -> AuditEventRecord: ...
    async def fetch_by_input_hash(self, input_hash: str) -> PersistedEvidenceBundle | None: ...
    async def fetch_training_candidates(self, limit: int) -> list[PersistedEvidenceBundle]: ...


class RepositoryProtocol(Protocol):
    def transaction(self, *, read_only: bool = False): ...
    async def fetch_by_input_hash(self, input_hash: str) -> PersistedEvidenceBundle | None: ...
    async def fetch_audit_chain(self) -> list[AuditEventRecord]: ...
    async def fetch_training_candidates(self, limit: int = 1000) -> list[PersistedEvidenceBundle]: ...


# ---------------------------------------------------------------------------
# PostgresRepositoryTransaction
# ---------------------------------------------------------------------------

class PostgresRepositoryTransaction:
    def __init__(self, repository: 'PostgresEvidenceRepository', *, read_only: bool = False) -> None:
        self._repository = repository
        self._read_only = read_only
        self._connection: asyncpg.Connection | None = None
        self._transaction: asyncpg.Transaction | None = None

    async def __aenter__(self) -> 'PostgresRepositoryTransaction':
        self._connection = await self._repository._pool.acquire(
            timeout=self._repository._connect_timeout_seconds
        )
        self._transaction = self._connection.transaction(
            isolation='read_committed', readonly=self._read_only
        )
        await self._transaction.start()
        # NOTE: statement_timeout and lock_timeout are set at connection-init
        # time via server_settings in create_pool(), eliminating the two
        # SET round-trips that previously occurred here on every transaction.
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        transaction = self._transaction
        connection = self._connection
        if transaction is None or connection is None:
            raise RepositoryStateError('Repository transaction exit called without an active connection')
        try:
            if exc_type is None:
                await transaction.commit()
            else:
                await transaction.rollback()
        finally:
            await self._repository._pool.release(connection)
            self._connection = None
            self._transaction = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _prepare(self, sql: str) -> asyncpg.PreparedStatement:
        connection = self._connection
        if connection is None:
            raise RepositoryStateError('Repository transaction is not active')
        return await connection.prepare(sql)

    async def _execute(self, sql: str, *args: object) -> str:
        statement = await self._prepare(sql)
        await statement.fetch(*args)
        return 'EXECUTED'

    async def _fetchrow(self, sql: str, *args: object) -> asyncpg.Record | None:
        statement = await self._prepare(sql)
        return await statement.fetchrow(*args)

    async def _fetch(self, sql: str, *args: object) -> list[asyncpg.Record]:
        statement = await self._prepare(sql)
        return await statement.fetch(*args)

    async def _fetchval(self, sql: str, *args: object) -> object:
        statement = await self._prepare(sql)
        return await statement.fetchval(*args)

    # ------------------------------------------------------------------
    # Session protocol implementation
    # ------------------------------------------------------------------

    async def acquire_audit_chain_lock(self, chain_id: int) -> None:
        """Acquire the per-chain advisory lock for chain_id (0 … 63).

        Replaces the former global AUDIT_CHAIN_LOCK_KEY lock.  Each of the 64
        chains has its own lock key, so independent chains proceed in parallel.
        """
        await self._fetchval(LOCK_AUDIT_CHAIN_SQL, chain_id_to_lock_key(chain_id))

    async def fetch_latest_audit_hash_for_chain(self, chain_id: int) -> str:
        """Return the most recent current_hash for the given chain partition."""
        value = await self._fetchval(FETCH_LATEST_AUDIT_HASH_FOR_CHAIN_SQL, chain_id)
        return str(value) if value is not None else ZERO_HASH

    async def check_duplicate(self, input_hash: str) -> bool:
        """Return True if input_hash already exists in requests (index-only scan)."""
        row = await self._fetchrow(CHECK_DUPLICATE_SQL, input_hash)
        return row is not None

    async def insert_records_batch(
        self,
        request: RequestRecord,
        result: ResultRecord,
        proof: ProofRecord,
    ) -> None:
        """Insert request, result, and proof in a single CTE round-trip.

        Raises DuplicateInputHashError on UniqueViolationError (duplicate
        input_hash).  The FK constraint results.request_id → requests.id is
        satisfied within the CTE by referencing the req RETURNING clause.
        """
        try:
            await self._execute(
                BATCH_INSERT_RECORDS_SQL,
                # req params
                request.id,
                request.input_hash,
                request.raw_input,
                request.created_at,
                # res params
                result.id,
                result.output_hash,
                result.raw_output,
                result.created_at,
                # prf params
                proof.id,
                proof.trace_hash,
                proof.final_proof,
                proof.integrity_hash,
                proof.proof_system,
                proof.circuit_hash,
                proof.verification_key_hash,
                proof.proof_bundle,
                proof.proof_verified,
                proof.created_at,
            )
        except asyncpg.UniqueViolationError as exc:
            raise DuplicateInputHashError(
                f'Duplicate input hash detected: {request.input_hash}'
            ) from exc

    async def insert_audit_event(self, record: AuditEventRecord) -> AuditEventRecord:
        audit_id = await self._fetchval(
            INSERT_AUDIT_SQL,
            record.chain_id,
            record.event_type,
            record.reference_id,
            record.event_payload,
            record.prev_hash,
            record.current_hash,
            record.created_at,
        )
        return record.model_copy(update={'id': int(audit_id)})

    async def fetch_by_input_hash(self, input_hash: str) -> PersistedEvidenceBundle | None:
        row = await self._fetchrow(FETCH_BUNDLE_SQL, input_hash)
        return self._repository._bundle_from_row(row)

    async def fetch_training_candidates(self, limit: int) -> list[PersistedEvidenceBundle]:
        rows = await self._fetch(FETCH_TRAINING_CANDIDATES_SQL, limit)
        return [
            bundle
            for bundle in (self._repository._bundle_from_row(row) for row in rows)
            if bundle is not None
        ]


# ---------------------------------------------------------------------------
# PostgresEvidenceRepository
# ---------------------------------------------------------------------------

class PostgresEvidenceRepository:
    def __init__(
        self,
        pool: asyncpg.Pool,
        *,
        statement_timeout_ms: int = 5000,
        lock_timeout_ms: int = 5000,
        connect_timeout_seconds: float = 5.0,
    ) -> None:
        self._pool = pool
        self._statement_timeout_ms = statement_timeout_ms
        self._lock_timeout_ms = lock_timeout_ms
        self._connect_timeout_seconds = connect_timeout_seconds

    def transaction(self, *, read_only: bool = False) -> PostgresRepositoryTransaction:
        return PostgresRepositoryTransaction(self, read_only=read_only)

    async def fetch_by_input_hash(self, input_hash: str) -> PersistedEvidenceBundle | None:
        async with self.transaction(read_only=True) as session:
            return await session.fetch_by_input_hash(input_hash)

    async def fetch_audit_chain(self) -> list[AuditEventRecord]:
        async with self.transaction(read_only=True) as session:
            rows = await session._fetch(FETCH_AUDIT_CHAIN_SQL)
            return [self._audit_from_row(row) for row in rows]

    async def fetch_training_candidates(self, limit: int = 1000) -> list[PersistedEvidenceBundle]:
        async with self.transaction(read_only=True) as session:
            return await session.fetch_training_candidates(limit)

    @staticmethod
    def _audit_from_row(row: asyncpg.Record | None) -> AuditEventRecord | None:
        if row is None:
            return None
        # Handle rows from FETCH_AUDIT_CHAIN_SQL (direct columns)
        # and rows from FETCH_BUNDLE_SQL (prefixed columns).
        if 'audit_id' in row:
            if row['audit_id'] is None:
                return None
            return AuditEventRecord(
                id=row['audit_id'],
                chain_id=row.get('audit_chain_id', 0) or 0,
                event_type=row['audit_event_type'],
                reference_id=row['audit_reference_id'],
                event_payload=row['audit_event_payload'],
                prev_hash=row['audit_prev_hash'],
                current_hash=row['audit_current_hash'],
                created_at=row['audit_created_at'],
            )
        return AuditEventRecord(
            id=row['id'],
            chain_id=row.get('chain_id', 0) or 0,
            event_type=row['event_type'],
            reference_id=row['reference_id'],
            event_payload=row['event_payload'],
            prev_hash=row['prev_hash'],
            current_hash=row['current_hash'],
            created_at=row['created_at'],
        )

    def _bundle_from_row(self, row: asyncpg.Record | None) -> PersistedEvidenceBundle | None:
        if row is None:
            return None
        return PersistedEvidenceBundle(
            request=RequestRecord(
                id=row['request_id'],
                input_hash=row['input_hash'],
                raw_input=row['raw_input'],
                created_at=row['request_created_at'],
            ),
            result=ResultRecord(
                id=row['result_id'],
                request_id=row['result_request_id'],
                output_hash=row['output_hash'],
                raw_output=row['raw_output'],
                created_at=row['result_created_at'],
            ),
            proof=ProofRecord(
                id=row['proof_id'],
                request_id=row['proof_request_id'],
                trace_hash=row['trace_hash'],
                final_proof=row['final_proof'],
                integrity_hash=row['integrity_hash'],
                proof_system=row['proof_system'],
                circuit_hash=row['circuit_hash'],
                verification_key_hash=row['verification_key_hash'],
                proof_bundle=row['proof_bundle'],
                proof_verified=row['proof_verified'],
                created_at=row['proof_created_at'],
            ),
            audit_log=self._audit_from_row(row),
        )
