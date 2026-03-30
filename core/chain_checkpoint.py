from __future__ import annotations
from dataclasses import dataclass
from core.audit_chain import ZERO_HASH, compute_audit_hash
from models.schemas import AuditChainVerificationResult
from utils.hashing import constant_time_equal, sha256_hex

CHECKPOINT_INTERVAL = 1000

@dataclass(frozen=True)
class ChainCheckpoint:
    chain_id: int
    segment_index: int
    last_record_id: int
    last_current_hash: str
    checkpoint_hash: str
    record_count: int

def compute_checkpoint_hash(*, chain_id, segment_index, last_record_id, last_current_hash):
    payload = f"checkpoint:{chain_id}:{segment_index}:{last_record_id}:{last_current_hash}"
    return sha256_hex(payload)

def build_checkpoints_for_chain(chain_id, records):
    checkpoints = []
    n_complete = len(records) // CHECKPOINT_INTERVAL
    for seg in range(n_complete):
        segs = records[seg * CHECKPOINT_INTERVAL : (seg+1) * CHECKPOINT_INTERVAL]
        last = segs[-1]
        cp_hash = compute_checkpoint_hash(chain_id=chain_id, segment_index=seg,
            last_record_id=last.id, last_current_hash=last.current_hash)
        checkpoints.append(ChainCheckpoint(chain_id=chain_id, segment_index=seg,
            last_record_id=last.id, last_current_hash=last.current_hash,
            checkpoint_hash=cp_hash, record_count=len(segs)))
    return checkpoints

@dataclass(frozen=True)
class SegmentVerificationResult:
    status: str
    reason: str
    chain_id: int
    segment_index: int
    checked_rows: int
    broken_record_id: int | None = None

def verify_segment(chain_id, segment_index, records, prev_hash, expected_checkpoint=None):
    current_hash = prev_hash
    for index, record in enumerate(records):
        if not constant_time_equal(record.prev_hash, current_hash):
            return SegmentVerificationResult(status="INVALID",
                reason="Previous hash mismatch in segment", chain_id=chain_id,
                segment_index=segment_index, checked_rows=index, broken_record_id=record.id)
        expected_hash = compute_audit_hash(prev_hash=record.prev_hash,
            event_type=record.event_type, reference_id=record.reference_id,
            event_payload=record.event_payload, created_at=record.created_at)
        if not constant_time_equal(record.current_hash, expected_hash):
            return SegmentVerificationResult(status="INVALID",
                reason="Current hash mismatch in segment", chain_id=chain_id,
                segment_index=segment_index, checked_rows=index, broken_record_id=record.id)
        current_hash = record.current_hash
    if expected_checkpoint is not None and records:
        last = records[-1]
        recomputed = compute_checkpoint_hash(chain_id=chain_id, segment_index=segment_index,
            last_record_id=last.id, last_current_hash=last.current_hash)
        if not constant_time_equal(recomputed, expected_checkpoint.checkpoint_hash):
            return SegmentVerificationResult(status="INVALID",
                reason="Checkpoint hash mismatch at segment boundary", chain_id=chain_id,
                segment_index=segment_index, checked_rows=len(records), broken_record_id=last.id)
    return SegmentVerificationResult(status="VALID", reason="Segment verified",
        chain_id=chain_id, segment_index=segment_index, checked_rows=len(records))

def verify_chain_with_checkpoints(chain_id, records, known_checkpoints=None):
    if not records:
        return AuditChainVerificationResult(status="VALID", reason="Chain is empty",
            checked_rows=0, last_hash=ZERO_HASH)
    cp_by_seg = {cp.segment_index: cp for cp in known_checkpoints} if known_checkpoints else {}
    n = len(records)
    n_complete = n // CHECKPOINT_INTERVAL
    prev_hash = ZERO_HASH
    total_checked = 0
    for seg in range(n_complete):
        segment = records[seg * CHECKPOINT_INTERVAL : (seg+1) * CHECKPOINT_INTERVAL]
        stored_cp = cp_by_seg.get(seg)
        if stored_cp is not None:
            recomputed = compute_checkpoint_hash(chain_id=chain_id, segment_index=seg,
                last_record_id=stored_cp.last_record_id, last_current_hash=stored_cp.last_current_hash)
            if constant_time_equal(recomputed, stored_cp.checkpoint_hash):
                prev_hash = stored_cp.last_current_hash
                total_checked += len(segment)
                continue
        result = verify_segment(chain_id, seg, segment, prev_hash, stored_cp)
        if result.status != "VALID":
            return AuditChainVerificationResult(status="INVALID", reason=result.reason,
                checked_rows=total_checked + result.checked_rows, last_hash=prev_hash,
                broken_record_id=result.broken_record_id)
        prev_hash = segment[-1].current_hash
        total_checked += result.checked_rows
    tail = records[n_complete * CHECKPOINT_INTERVAL :]
    if tail:
        result = verify_segment(chain_id, n_complete, tail, prev_hash)
        if result.status != "VALID":
            return AuditChainVerificationResult(status="INVALID", reason=result.reason,
                checked_rows=total_checked + result.checked_rows, last_hash=prev_hash,
                broken_record_id=result.broken_record_id)
        total_checked += result.checked_rows
        prev_hash = tail[-1].current_hash
    return AuditChainVerificationResult(status="VALID",
        reason=f"Chain verified with checkpoints ({n_complete} complete segment(s))",
        checked_rows=total_checked, last_hash=prev_hash)
