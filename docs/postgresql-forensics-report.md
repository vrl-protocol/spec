# PostgreSQL Forensics Report

## Objective

Document how the Verifiable Reality Layer persists each deterministic computation as immutable, replayable forensic evidence.

## Schema

Tables:
- `requests`
- `results`
- `proofs`
- `audit_log`

Each successful computation persists:
1. canonical request evidence
2. canonical result evidence
3. proof evidence
4. chained audit evidence

## Immutability controls

Implemented in `migrations/001_init.sql`:
- `BEFORE UPDATE OR DELETE` triggers on all evidence tables
- explicit `REVOKE UPDATE, DELETE, TRUNCATE`
- row-level security with `FORCE ROW LEVEL SECURITY`
- least-privilege roles:
  - `vrl_writer` for `INSERT`
  - `vrl_reader` for `SELECT`

## Hash chain design

Each `audit_log` row contains:
- `prev_hash`
- `current_hash`
- `event_payload`
- `event_type`
- `reference_id`
- `created_at`

`current_hash` is derived as:
- `SHA256(prev_hash + canonical(event_payload + metadata))`

This allows:
- tamper detection
- chronological replay
- independent chain verification

## Atomic write path

Implemented in `app/services/evidence_service.py` and `app/db/repository.py`.

Transaction flow:
1. validate input
2. compute deterministic result
3. generate proof artifact
4. insert `requests`
5. insert `results`
6. insert `proofs`
7. insert `audit_log`
8. reload persisted bundle
9. recompute and verify proof before commit

If any step fails:
- transaction rolls back
- failure event is logged in a separate append-only audit transaction

## Concurrency protection

The audit chain is serialized using `pg_advisory_xact_lock` so only one transaction can advance the chain at a time.

## Verification path

Implemented in:
- `app/services/evidence_service.py`
- `core/verifier.py`
- `core/audit_chain.py`
- `scripts/verify_audit_chain.py`

Verification performs:
- recomputation from original request
- constant-time hash comparison
- persisted evidence comparison
- audit-chain recomputation and validation

## Automated coverage

Tests covering database evidence behavior:
- `tests/test_db_persistence.py`
- `tests/test_db_verification.py`
- `tests/test_append_only_and_rollback.py`
- `tests/test_replay_protection.py`
- `tests/test_audit_chain.py`
- `tests/test_concurrency.py`

## Validation status

- append-only enforcement -> **PASS**
- rollback on failure -> **PASS**
- duplicate input replay detection -> **PASS**
- audit-chain tamper detection -> **PASS**
- deterministic recomputation from persisted evidence -> **PASS**
- concurrency safety in the chain update path -> **PASS**

## Operational note

Live validation was completed against a local PostgreSQL 17.9 instance. The append-only controls, tamper-detection path, rollback behavior, replay verification, and concurrency integrity checks all passed.

Measured latency remained above the target envelope:
- request latency `p95`: `436.05ms`
- DB transaction latency `p95`: `233.54ms`
- lock wait latency `p95`: `24.03ms`

The audit-chain serialization lock is the dominant bottleneck. The evidence model is valid, but the current implementation is not yet performance-ready for the stated `< 100ms` preferred target without additional optimization.

The validated local PostgreSQL server had `ssl = off`, so transport TLS remains a required production deployment control.
