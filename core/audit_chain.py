from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid5

from models.schemas import AuditChainVerificationResult, AuditEventRecord
from utils.canonical import canonical_json
from utils.hashing import constant_time_equal, sha256_hex
from utils.time import utc_isoformat

EVIDENCE_NAMESPACE = UUID("d9ec1f3e-2d27-45d4-af5f-d8d5efcb7c1e")
ZERO_HASH = "0" * 64

# Number of independent audit chains.  Each write maps deterministically to
# one chain via:  chain_id = int(input_hash, 16) % AUDIT_CHAIN_PARTITIONS
# This replaces the single global advisory lock with 64 per-chain locks,
# reducing serialization contention by ~64× under uniform hash distribution.
AUDIT_CHAIN_PARTITIONS = 64


def chain_id_for_input(input_hash: str) -> int:
    """Return the partition index (0 … AUDIT_CHAIN_PARTITIONS-1) for input_hash."""
    return int(input_hash, 16) % AUDIT_CHAIN_PARTITIONS


def deterministic_request_id(input_hash: str) -> UUID:
    return uuid5(EVIDENCE_NAMESPACE, f"request:{input_hash}")


def deterministic_result_id(request_id: UUID, output_hash: str) -> UUID:
    return uuid5(EVIDENCE_NAMESPACE, f"result:{request_id}:{output_hash}")


def deterministic_proof_id(request_id: UUID, final_proof: str) -> UUID:
    return uuid5(EVIDENCE_NAMESPACE, f"proof:{request_id}:{final_proof}")


def audit_hash_payload(
    *,
    event_type: str,
    reference_id: UUID | None,
    event_payload: dict[str, object],
    created_at: datetime,
) -> dict[str, object]:
    return {
        "event_type": event_type,
        "reference_id": str(reference_id) if reference_id is not None else None,
        "event_payload": event_payload,
        "created_at": utc_isoformat(created_at),
    }


def compute_audit_hash(
    *,
    prev_hash: str,
    event_type: str,
    reference_id: UUID | None,
    event_payload: dict[str, object],
    created_at: datetime,
) -> str:
    payload = canonical_json(
        audit_hash_payload(
            event_type=event_type,
            reference_id=reference_id,
            event_payload=event_payload,
            created_at=created_at,
        )
    )
    return sha256_hex(prev_hash + payload)


def build_audit_event(
    *,
    event_type: str,
    reference_id: UUID | None,
    event_payload: dict[str, object],
    prev_hash: str,
    created_at: datetime,
    chain_id: int = 0,
    id: int | None = None,
) -> AuditEventRecord:
    current_hash = compute_audit_hash(
        prev_hash=prev_hash,
        event_type=event_type,
        reference_id=reference_id,
        event_payload=event_payload,
        created_at=created_at,
    )
    return AuditEventRecord(
        id=id,
        chain_id=chain_id,
        event_type=event_type,
        reference_id=reference_id,
        event_payload=event_payload,
        prev_hash=prev_hash,
        current_hash=current_hash,
        created_at=created_at,
    )


def _verify_single_chain(records: list[AuditEventRecord]) -> AuditChainVerificationResult:
    """Validate one partition's chain: ZERO_HASH → hash_1 → … → hash_n."""
    previous_hash = ZERO_HASH
    for index, record in enumerate(records):
        if not constant_time_equal(record.prev_hash, previous_hash):
            return AuditChainVerificationResult(
                status="INVALID",
                reason="Previous hash mismatch detected in audit chain",
                checked_rows=index,
                last_hash=previous_hash,
                broken_record_id=record.id,
            )
        expected_hash = compute_audit_hash(
            prev_hash=record.prev_hash,
            event_type=record.event_type,
            reference_id=record.reference_id,
            event_payload=record.event_payload,
            created_at=record.created_at,
        )
        if not constant_time_equal(record.current_hash, expected_hash):
            return AuditChainVerificationResult(
                status="INVALID",
                reason="Current hash mismatch detected in audit chain",
                checked_rows=index,
                last_hash=previous_hash,
                broken_record_id=record.id,
            )
        previous_hash = record.current_hash

    return AuditChainVerificationResult(
        status="VALID",
        reason="Audit chain verified successfully",
        checked_rows=len(records),
        last_hash=previous_hash,
        broken_record_id=None,
    )


def verify_audit_chain(records: list[AuditEventRecord]) -> AuditChainVerificationResult:
    """Validate all partition chains.

    Records may span multiple chain_ids (partitioned mode) or all have
    chain_id=0 (legacy / in-memory mode).  Each chain is validated
    independently from ZERO_HASH.  The overall result is VALID only when
    every chain is individually VALID.

    The caller must supply records ordered by (chain_id ASC, id ASC) — that
    is the order returned by FETCH_AUDIT_CHAIN_SQL.
    """
    if not records:
        return AuditChainVerificationResult(
            status="VALID",
            reason="Audit chain is empty",
            checked_rows=0,
            last_hash=ZERO_HASH,
        )

    # Group records by chain_id, preserving insertion order within each chain.
    chains: dict[int, list[AuditEventRecord]] = {}
    for record in records:
        cid = record.chain_id
        if cid not in chains:
            chains[cid] = []
        chains[cid].append(record)

    total_checked = 0
    for cid in sorted(chains):
        result = _verify_single_chain(chains[cid])
        if result.status != "VALID":
            return result
        total_checked += result.checked_rows

    n_chains = len(chains)
    return AuditChainVerificationResult(
        status="VALID",
        reason=f"All {n_chains} audit chain partition(s) verified successfully",
        checked_rows=total_checked,
        last_hash=records[-1].current_hash,
    )
