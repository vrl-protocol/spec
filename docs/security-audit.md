# Security Audit Report

## Scope

Security review and hardening were applied across:
- `app/`
- `api/`
- `core/`
- `models/`
- `utils/`
- `security/`
- `scripts/`
- `migrations/`

## Module review

### 1. Input validation layer
- Strict Pydantic validation enforces field presence, type correctness, positive numeric values, and import-specific constraints.
- Request bodies are size-limited before JSON parsing.
- Payload guards reject injection-like strings, floats in guarded paths, malformed objects, and unsupported shapes.
- Canonicalization is deterministic and normalizes `Decimal`, date/time values, UUIDs, mappings, and sequences.
- Status: **PASS**

### 2. Deterministic calculation engine
- Core computation uses `Decimal` exclusively.
- No floating-point arithmetic occurs in tariff, Section 301, MPF, HMF, or landed-cost calculations.
- Rounding is explicit and centralized.
- No network or external mutable dependency exists in the computation path.
- Status: **PASS**

### 3. Local data integrity layer
- Tariff data is stored locally and versioned.
- Dataset hash is recomputed and included in every result.
- Tariff lookup fails closed when a rule is missing.
- Status: **PASS**

### 4. Proof generation layer
- Input, output, and trace values are canonicalized before hashing.
- `final_proof` is derived from `input_hash + output_hash + trace_hash`.
- Stored proof values are revalidated against recomputed evidence before a transaction is accepted as successful.
- Status: **PASS**

### 5. PostgreSQL evidence layer
- The database schema is append-only by trigger and privilege design.
- `UPDATE`, `DELETE`, and `TRUNCATE` are revoked and rejected.
- `read_committed` transactions enforce the atomic request/result/proof/audit write boundary, while `pg_advisory_xact_lock` serializes audit-chain advancement safely under concurrency.
- The audit chain is serialized with `pg_advisory_xact_lock` to avoid race conditions.
- Repository queries are parameterized prepared statements only.
- Status: **PASS**

### 6. API hardening
- `/calculate` and `/verify` fail closed when the database repository is not configured.
- Unexpected internal failures return sanitized `500` responses without stack traces.
- Duplicate input hashes return `409`.
- Rate limiting is enforced at the API edge.
- Diagnostic `/run` no longer uses a hidden default payload and requires explicit input.
- Status: **PASS**

### 7. Audit trail and evidence chain
- PostgreSQL `audit_log` is the sole forensic truth source.
- Each audit event includes a chained hash derived from the previous audit hash and canonical event payload.
- Legacy file-based audit logging is disabled to prevent split-brain evidence.
- Status: **PASS**

### 8. Verification module
- Persisted verification recomputes the landed-cost response from the original request.
- Stored request, result, proof, and audit hashes are compared using constant-time comparisons.
- Audit-chain integrity is checked independently and can invalidate an otherwise matching result.
- Status: **PASS**

## Attack simulation coverage

Validated by automated tests:
- duplicate input replay detection
- append-only update/delete rejection
- transaction rollback on partial failure
- audit-chain tampering detection
- concurrent persistence safety
- invalid input rejection
- proof tampering rejection

## Static analysis and tests

- `python -m pytest -q` -> **20 passed**
- `ruff check .` -> **clean**
- `bandit -r app api core models utils security scripts -q` -> **clean**

## Residual notes

- Live validation was completed against PostgreSQL 17.9 with append-only enforcement, tamper detection, replay verification, rollback checks, and adversarial input rejection all passing.
- The validated local PostgreSQL instance had `ssl = off`, so transport TLS is still a required production deployment control.
- The write path is correct and safe, but the audit-chain serialization lock keeps `p95` request latency above `100ms` in the current design.

## Conclusion

The system now treats PostgreSQL as immutable, cryptographically verifiable evidence storage rather than general application persistence.

Status: **PASS**
