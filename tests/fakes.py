from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import dataclass, field

from app.db.repository import AppendOnlyViolationError, DuplicateInputHashError
from core.audit_chain import ZERO_HASH
from models.schemas import AuditEventRecord, PersistedEvidenceBundle, ProofRecord, RequestRecord, ResultRecord


class InjectedFailure(RuntimeError):
    pass


@dataclass
class _RepositoryState:
    requests_by_input_hash: dict[str, RequestRecord] = field(default_factory=dict)
    results_by_request_id: dict[object, ResultRecord] = field(default_factory=dict)
    proofs_by_request_id: dict[object, ProofRecord] = field(default_factory=dict)
    audit_log: list[AuditEventRecord] = field(default_factory=list)

    def clone(self) -> '_RepositoryState':
        return deepcopy(self)


class InMemoryRepositoryTransaction:
    def __init__(self, repository: 'InMemoryEvidenceRepository', *, read_only: bool = False) -> None:
        self._repository = repository
        self._read_only = read_only
        self._working_state: _RepositoryState | None = None

    async def __aenter__(self) -> 'InMemoryRepositoryTransaction':
        await self._repository._lock.acquire()
        self._working_state = self._repository._state.clone()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        try:
            if exc_type is None and not self._read_only and self._working_state is not None:
                self._repository._state = self._working_state
        finally:
            self._repository._lock.release()

    @property
    def _state(self) -> _RepositoryState:
        assert self._working_state is not None
        return self._working_state

    def _maybe_fail(self, operation: str) -> None:
        if self._repository.fail_on == operation:
            raise InjectedFailure(f'injected failure during {operation}')

    # ------------------------------------------------------------------
    # Updated Protocol implementation
    # ------------------------------------------------------------------

    async def acquire_audit_chain_lock(self, chain_id: int) -> None:
        # The repository-level asyncio.Lock (acquired in __aenter__) already
        # serialises all in-memory transactions.  Per-chain locking in the
        # real PostgreSQL implementation is a no-op here.
        return None

    async def fetch_latest_audit_hash_for_chain(self, chain_id: int) -> str:
        """Return the last current_hash for records belonging to chain_id."""
        chain_records = [r for r in self._state.audit_log if r.chain_id == chain_id]
        if not chain_records:
            return ZERO_HASH
        return chain_records[-1].current_hash

    async def check_duplicate(self, input_hash: str) -> bool:
        return input_hash in self._state.requests_by_input_hash

    async def insert_records_batch(
        self,
        request: RequestRecord,
        result: ResultRecord,
        proof: ProofRecord,
    ) -> None:
        """Insert request, result, proof atomically (mirrors the CTE batch)."""
        self._maybe_fail('insert_request')
        if request.input_hash in self._state.requests_by_input_hash:
            raise DuplicateInputHashError(
                f'Duplicate input hash detected: {request.input_hash}'
            )
        self._maybe_fail('insert_result')
        self._maybe_fail('insert_proof')
        self._state.requests_by_input_hash[request.input_hash] = request.model_copy(deep=True)
        self._state.results_by_request_id[result.request_id] = result.model_copy(deep=True)
        self._state.proofs_by_request_id[proof.request_id] = proof.model_copy(deep=True)

    async def insert_audit_event(self, record: AuditEventRecord) -> AuditEventRecord:
        self._maybe_fail('insert_audit_event')
        inserted = record.model_copy(update={'id': len(self._state.audit_log) + 1}, deep=True)
        self._state.audit_log.append(inserted)
        return inserted

    async def fetch_by_input_hash(self, input_hash: str) -> PersistedEvidenceBundle | None:
        request = self._state.requests_by_input_hash.get(input_hash)
        if request is None:
            return None
        result = self._state.results_by_request_id.get(request.id)
        proof = self._state.proofs_by_request_id.get(request.id)
        if result is None or proof is None:
            return None
        audit_log = None
        for record in reversed(self._state.audit_log):
            if record.reference_id == request.id:
                audit_log = record.model_copy(deep=True)
                break
        return PersistedEvidenceBundle(
            request=request.model_copy(deep=True),
            result=result.model_copy(deep=True),
            proof=proof.model_copy(deep=True),
            audit_log=audit_log,
        )


class InMemoryEvidenceRepository:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._state = _RepositoryState()
        self.fail_on: str | None = None

    def transaction(self, *, read_only: bool = False) -> InMemoryRepositoryTransaction:
        return InMemoryRepositoryTransaction(self, read_only=read_only)

    async def fetch_by_input_hash(self, input_hash: str) -> PersistedEvidenceBundle | None:
        async with self.transaction(read_only=True) as session:
            return await session.fetch_by_input_hash(input_hash)

    async def fetch_audit_chain(self) -> list[AuditEventRecord]:
        async with self.transaction(read_only=True):
            # Return all records sorted by (chain_id, id) — same order as
            # FETCH_AUDIT_CHAIN_SQL — so that verify_audit_chain() can group
            # them correctly without extra sorting.
            return sorted(
                (record.model_copy(deep=True) for record in self._state.audit_log),
                key=lambda r: (r.chain_id, r.id or 0),
            )

    def attempt_update_request(self) -> None:
        raise AppendOnlyViolationError('Append-only repository rejects updates')

    def attempt_delete_request(self) -> None:
        raise AppendOnlyViolationError('Append-only repository rejects deletes')

    def tamper_result_landed_cost(self, input_hash: str, landed_cost: str) -> None:
        request = self._state.requests_by_input_hash[input_hash]
        result = self._state.results_by_request_id[request.id]
        raw_output = deepcopy(result.raw_output)
        raw_output['result']['landed_cost'] = landed_cost
        self._state.results_by_request_id[request.id] = result.model_copy(
            update={'raw_output': raw_output}, deep=True
        )

    def tamper_audit_hash(self, index: int, new_hash: str) -> None:
        record = self._state.audit_log[index]
        self._state.audit_log[index] = record.model_copy(
            update={'current_hash': new_hash}, deep=True
        )

    @property
    def request_count(self) -> int:
        return len(self._state.requests_by_input_hash)

    @property
    def result_count(self) -> int:
        return len(self._state.results_by_request_id)

    @property
    def proof_count(self) -> int:
        return len(self._state.proofs_by_request_id)

    @property
    def audit_count(self) -> int:
        return len(self._state.audit_log)
