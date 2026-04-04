from __future__ import annotations

import asyncio

import asyncpg
from pydantic import ValidationError

from app.db.repository import DuplicateInputHashError, PersistenceIntegrityError, RepositoryProtocol, RepositoryUnavailableError
from backend.proof_export import export_proof_bundle, verify_proof_bundle
from backend.trace_adapter import build_trace_packet
from backend.verified_dataset import build_verified_training_record
from core.audit_chain import (
    build_audit_event,
    chain_id_for_input,
    compute_audit_hash,
    deterministic_proof_id,
    deterministic_request_id,
    deterministic_result_id,
    verify_audit_chain,
)
from core.chain_metrics import chain_metrics
from core.engine import calculate_import_landed_cost
from core.verifier import verify_proof
from models.schemas import (
    CalculationResponse,
    ImportCalculationRequest,
    PersistedCalculationResponse,
    PersistedEvidenceBundle,
    PersistedVerificationResponse,
    ProofRecord,
    RequestRecord,
    ResultRecord,
    VerificationResult,
)
from utils.canonical import canonical_json
from utils.hashing import constant_time_equal
from utils.time import utc_now
from zk.provers.plonk_prover import build_plonk_proof
from zk.interfaces import Proof
from zk.verifiers.plonk_verifier import verify_plonk_proof


MAX_TRANSACTION_RETRIES = 5
RETRY_BACKOFF_SECONDS = 0.05
RETRYABLE_DB_ERRORS = (asyncpg.SerializationError, asyncpg.DeadlockDetectedError)


class EvidenceService:
    def __init__(self, repository: RepositoryProtocol | None) -> None:
        self._repository = repository

    def _require_repository(self) -> RepositoryProtocol:
        if self._repository is None:
            raise RepositoryUnavailableError('Database evidence repository is not configured')
        return self._repository

    async def calculate_and_persist(self, request_payload: object) -> PersistedCalculationResponse:
        repository = self._require_repository()
        request = ImportCalculationRequest.model_validate(request_payload)

        # ----------------------------------------------------------------
        # Phase 1 — compute (outside any transaction, no lock held)
        # ----------------------------------------------------------------
        response = calculate_import_landed_cost(request)
        trace_packet = build_trace_packet(request.model_dump(mode='python'), produced_by='evidence_service', cycle=1)
        zk_proof = build_plonk_proof(
            trace_packet.witness_artifact,
            trace_packet.trace_artifact.trace_hash,
            produced_by='evidence_service',
            cycle=1,
        )
        zk_verification = verify_plonk_proof(zk_proof, produced_by='evidence_service', cycle=1)
        if zk_verification.status != 'VALID':
            raise PersistenceIntegrityError(f'ZK proof verification failed before persistence: {zk_verification.reason}')
        proof_bundle = export_proof_bundle(
            request.model_dump(mode='python'),
            packet=trace_packet,
            proof=zk_proof,
        )
        bundle_verification = verify_proof_bundle(proof_bundle)
        if not bundle_verification['valid']:
            raise PersistenceIntegrityError(
                f"Exported proof bundle failed offline verification: {bundle_verification['reason']}"
            )
        created_at = utc_now()
        request_record, result_record, proof_record = self._build_records(
            request,
            response,
            created_at,
            zk_proof=zk_proof,
            proof_bundle=proof_bundle,
            verification_key_hash=bundle_verification['verification_key_hash'],
        )

        # Derive the partition once; used for the lock key and hash fetch.
        chain_id = chain_id_for_input(request_record.input_hash)

        # Record the request against this chain partition.
        chain_metrics.record_request(chain_id)

        # ----------------------------------------------------------------
        # Phase 2 — persist (transaction scope is ONLY DB writes)
        # ----------------------------------------------------------------
        # Key architectural changes vs the previous implementation:
        #
        # 1. Per-chain advisory lock (chain_id 0-63) instead of one global
        #    lock.  Under uniform hash distribution this reduces serialization
        #    contention ~64×.
        #
        # 2. prev_hash fetched BEFORE inserts (while holding the chain lock)
        #    so that no second hash fetch is needed after inserts.
        #
        # 3. Lightweight duplicate check (index-only scan) replaces the full
        #    JOIN bundle read inside the critical section.
        #
        # 4. Batched CTE insert (request + result + proof in one round-trip)
        #    replaces three sequential INSERT statements.
        #
        # 5. The in-transaction bundle re-fetch + full proof recomputation
        #    (verify_proof → calculate_import_landed_cost) have been removed.
        #    A lightweight in-memory audit hash consistency check replaces them.
        #    The persisted_response is built from the in-memory records instead
        #    of a post-insert DB re-read; the records are correct by construction
        #    (any INSERT failure raises and rolls back the transaction).

        for attempt in range(1, MAX_TRANSACTION_RETRIES + 1):
            duplicate_error: DuplicateInputHashError | None = None
            persisted_response: PersistedCalculationResponse | None = None
            try:
                async with repository.transaction() as session:
                    # --- acquire per-chain lock (timed for hotspot detection) ---
                    with chain_metrics.timed_lock_wait(chain_id):
                        await session.acquire_audit_chain_lock(chain_id)

                    # --- fetch prev_hash for this chain (while locked) ---
                    prev_hash = await session.fetch_latest_audit_hash_for_chain(chain_id)

                    # --- lightweight duplicate check ---
                    is_duplicate = await session.check_duplicate(request_record.input_hash)
                    if is_duplicate:
                        duplicate_audit = build_audit_event(
                            event_type='calculation_rejected_duplicate',
                            reference_id=request_record.id,
                            event_payload={
                                'input_hash': request_record.input_hash,
                                'reason': 'duplicate_input_hash',
                            },
                            prev_hash=prev_hash,
                            created_at=created_at,
                            chain_id=chain_id,
                        )
                        await session.insert_audit_event(duplicate_audit)
                        duplicate_error = DuplicateInputHashError(
                            f'Duplicate input hash detected: {request_record.input_hash}'
                        )
                    else:
                        # --- batch insert (1 round-trip) ---
                        await session.insert_records_batch(request_record, result_record, proof_record)

                        # --- build and insert the audit event ---
                        audit_record = build_audit_event(
                            event_type='calculation_persisted',
                            reference_id=request_record.id,
                            event_payload={
                                'request_id': str(request_record.id),
                                'result_id': str(result_record.id),
                                'proof_id': str(proof_record.id),
                                'input_hash': request_record.input_hash,
                                'output_hash': result_record.output_hash,
                                'trace_hash': proof_record.trace_hash,
                                'integrity_hash': proof_record.integrity_hash,
                            },
                            prev_hash=prev_hash,
                            created_at=created_at,
                            chain_id=chain_id,
                        )
                        inserted_audit = await session.insert_audit_event(audit_record)

                        # --- lightweight in-memory audit hash sanity check ---
                        # This verifies that compute_audit_hash is deterministic
                        # and that prev_hash was threaded correctly.  It is O(1)
                        # pure Python with no additional round-trips.
                        expected_current_hash = compute_audit_hash(
                            prev_hash=prev_hash,
                            event_type=audit_record.event_type,
                            reference_id=audit_record.reference_id,
                            event_payload=audit_record.event_payload,
                            created_at=audit_record.created_at,
                        )
                        if not constant_time_equal(inserted_audit.current_hash, expected_current_hash):
                            raise PersistenceIntegrityError(
                                'Audit event current_hash does not match recomputed audit hash'
                            )

                        # --- build response from in-memory records (no re-fetch) ---
                        synthetic_bundle = PersistedEvidenceBundle(
                            request=request_record,
                            result=result_record,
                            proof=proof_record,
                            audit_log=inserted_audit,
                        )
                        persisted_response = PersistedCalculationResponse(
                            result=response.result,
                            trace=response.trace,
                            integrity=response.integrity,
                            evidence=synthetic_bundle,
                        )
                        build_verified_training_record(
                            persisted_response,
                            zk_proof=zk_proof,
                            witness_hash=trace_packet.witness_artifact.witness_hash,
                            verification_key_hash=bundle_verification['verification_key_hash'],
                            proof_bundle=proof_bundle,
                        )

                if duplicate_error is not None:
                    chain_metrics.record_duplicate(chain_id)
                    raise duplicate_error
                if persisted_response is None:
                    raise PersistenceIntegrityError(
                        'Persisted response was not produced for a successful transaction'
                    )
                chain_metrics.record_success(chain_id)
                return persisted_response

            except DuplicateInputHashError:
                raise
            except RETRYABLE_DB_ERRORS as exc:
                if attempt == MAX_TRANSACTION_RETRIES:
                    await self._log_failure_event(
                        repository=repository,
                        reference_id=request_record.id,
                        input_hash=request_record.input_hash,
                        chain_id=chain_id,
                        reason=f'retry_exhausted:{type(exc).__name__}:{exc}',
                    )
                    raise
                await asyncio.sleep(RETRY_BACKOFF_SECONDS * attempt)
            except Exception as exc:
                chain_metrics.record_error(chain_id)
                await self._log_failure_event(
                    repository=repository,
                    reference_id=request_record.id,
                    input_hash=request_record.input_hash,
                    chain_id=chain_id,
                    reason=str(exc),
                )
                raise

        raise PersistenceIntegrityError('Transaction retries exhausted without a terminal outcome')

    async def verify_persisted(self, request_payload: object) -> PersistedVerificationResponse:
        repository = self._require_repository()
        request = ImportCalculationRequest.model_validate(request_payload)
        recomputed = calculate_import_landed_cost(request)
        input_hash = recomputed.integrity.input_hash
        stored = await repository.fetch_by_input_hash(input_hash)
        audit_chain = await self.verify_audit_chain()
        if stored is None:
            verification = VerificationResult(
                status='INVALID',
                reason='No persisted evidence found for the supplied input hash',
                recomputed_input_hash=recomputed.integrity.input_hash,
                recomputed_output_hash=recomputed.integrity.output_hash,
                recomputed_trace_hash=recomputed.integrity.trace_hash,
                recomputed_integrity_hash=recomputed.integrity.integrity_hash,
            )
            return PersistedVerificationResponse(verification=verification, evidence=None, audit_chain=audit_chain)

        verification = self._verify_bundle(request, stored)
        if audit_chain.status != 'VALID' and verification.status == 'VALID':
            verification = VerificationResult(
                status='INVALID',
                reason='Audit chain integrity check failed',
                recomputed_input_hash=verification.recomputed_input_hash,
                recomputed_output_hash=verification.recomputed_output_hash,
                recomputed_trace_hash=verification.recomputed_trace_hash,
                recomputed_integrity_hash=verification.recomputed_integrity_hash,
            )
        return PersistedVerificationResponse(verification=verification, evidence=stored, audit_chain=audit_chain)

    async def verify_audit_chain(self):
        repository = self._require_repository()
        records = await repository.fetch_audit_chain()
        return verify_audit_chain(records)

    def _build_records(
        self,
        request: ImportCalculationRequest,
        response: CalculationResponse,
        created_at,
        *,
        zk_proof,
        proof_bundle: dict[str, object],
        verification_key_hash: str,
    ) -> tuple[RequestRecord, ResultRecord, ProofRecord]:
        request_json = request.model_dump(mode='json')
        response_json = response.model_dump(mode='json')
        request_id = deterministic_request_id(response.integrity.input_hash)
        result_id = deterministic_result_id(request_id, response.integrity.output_hash)
        proof_id = deterministic_proof_id(request_id, zk_proof.final_proof)
        return (
            RequestRecord(
                id=request_id,
                input_hash=response.integrity.input_hash,
                raw_input=request_json,
                created_at=created_at,
            ),
            ResultRecord(
                id=result_id,
                request_id=request_id,
                output_hash=response.integrity.output_hash,
                raw_output=response_json,
                created_at=created_at,
            ),
            ProofRecord(
                id=proof_id,
                request_id=request_id,
                trace_hash=response.integrity.trace_hash,
                final_proof=zk_proof.final_proof,
                integrity_hash=response.integrity.integrity_hash,
                proof_system=zk_proof.proof_system,
                circuit_hash=zk_proof.circuit_hash,
                verification_key_hash=verification_key_hash,
                proof_bundle=proof_bundle,
                proof_verified=True,
                created_at=created_at,
            ),
        )

    def _verify_bundle(
        self,
        request: ImportCalculationRequest,
        evidence: PersistedEvidenceBundle,
    ) -> VerificationResult:
        expected_request_json = request.model_dump(mode='json')
        stored_request_json = evidence.request.raw_input
        if not constant_time_equal(
            canonical_json(expected_request_json), canonical_json(stored_request_json)
        ):
            return self._invalid_verification(
                request, 'Stored request payload does not match canonical request data'
            )

        if evidence.proof.proof_system != 'plonk':
            return self._invalid_verification(request, 'legacy record')
        try:
            stored_response = CalculationResponse.model_validate(evidence.result.raw_output)
        except ValidationError as exc:
            return self._invalid_verification(request, f'Invalid stored calculation response: {exc}')
        verification = verify_proof(
            request.model_dump(mode='python'), stored_response.model_dump(mode='python')
        )
        if verification.status != 'VALID':
            return verification
        if not constant_time_equal(evidence.request.input_hash, verification.recomputed_input_hash):
            return self._invalid_verification(
                request, 'Stored request hash does not match recomputed input hash'
            )
        if not constant_time_equal(evidence.result.output_hash, verification.recomputed_output_hash):
            return self._invalid_verification(
                request, 'Stored result hash does not match recomputed output hash'
            )
        if not constant_time_equal(evidence.proof.trace_hash, verification.recomputed_trace_hash):
            return self._invalid_verification(
                request, 'Stored trace hash does not match recomputed trace hash'
            )
        if not evidence.proof.proof_verified:
            return self._invalid_verification(
                request, 'Stored proof is not marked as verified'
            )
        bundle_verification = verify_proof_bundle(evidence.proof.proof_bundle)
        if not bundle_verification['valid']:
            return self._invalid_verification(
                request, f"Stored proof bundle failed offline verification: {bundle_verification['reason']}"
            )
        try:
            bundled_proof = Proof.model_validate(evidence.proof.proof_bundle.get('proof'))
        except ValidationError as exc:
            return self._invalid_verification(request, f'Invalid stored proof bundle: {exc}')
        if not constant_time_equal(stored_response.integrity.output_hash, evidence.result.output_hash):
            return self._invalid_verification(
                request, 'Stored response integrity does not match persisted result hash'
            )
        if not constant_time_equal(stored_response.integrity.trace_hash, evidence.proof.trace_hash):
            return self._invalid_verification(
                request, 'Stored response integrity does not match persisted trace hash'
            )
        if not constant_time_equal(bundled_proof.final_proof, evidence.proof.final_proof):
            return self._invalid_verification(request, 'Stored ZK proof does not match bundled final proof')
        if not constant_time_equal(bundled_proof.circuit_hash, evidence.proof.circuit_hash):
            return self._invalid_verification(request, 'Stored circuit hash does not match bundled circuit hash')
        if not constant_time_equal(
            bundled_proof.proof_blob_hex,
            str(evidence.proof.proof_bundle.get('proof', {}).get('proof_blob_hex', '')),
        ):
            return self._invalid_verification(request, 'Stored proof bundle proof bytes are invalid')
        if evidence.audit_log is not None:
            expected_audit_hash = compute_audit_hash(
                prev_hash=evidence.audit_log.prev_hash,
                event_type=evidence.audit_log.event_type,
                reference_id=evidence.audit_log.reference_id,
                event_payload=evidence.audit_log.event_payload,
                created_at=evidence.audit_log.created_at,
            )
            if not constant_time_equal(evidence.audit_log.current_hash, expected_audit_hash):
                return self._invalid_verification(
                    request, 'Stored audit event hash does not match recomputed audit hash'
                )
        return verification

    def _invalid_verification(
        self, request: ImportCalculationRequest, reason: str
    ) -> VerificationResult:
        recomputed = calculate_import_landed_cost(request)
        return VerificationResult(
            status='INVALID',
            reason=reason,
            recomputed_input_hash=recomputed.integrity.input_hash,
            recomputed_output_hash=recomputed.integrity.output_hash,
            recomputed_trace_hash=recomputed.integrity.trace_hash,
            recomputed_integrity_hash=recomputed.integrity.integrity_hash,
        )

    async def _log_failure_event(
        self,
        *,
        repository: RepositoryProtocol,
        reference_id,
        input_hash: str,
        chain_id: int,
        reason: str,
    ) -> None:
        created_at = utc_now()
        async with repository.transaction() as session:
            await session.acquire_audit_chain_lock(chain_id)
            prev_hash = await session.fetch_latest_audit_hash_for_chain(chain_id)
            failure_event = build_audit_event(
                event_type='calculation_persist_failed',
                reference_id=reference_id,
                event_payload={
                    'input_hash': input_hash,
                    'reason': reason,
                },
                prev_hash=prev_hash,
                created_at=created_at,
                chain_id=chain_id,
            )
            await session.insert_audit_event(failure_event)
