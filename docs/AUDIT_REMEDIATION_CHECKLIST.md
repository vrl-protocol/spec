# Audit Remediation Checklist

This checklist converts the March 30, 2026 full-system audit into an execution plan.

Status legend:
- `[ ]` not started
- `[-]` in progress
- `[x]` complete

## 1. Canonical Evidence Path

- [ ] Make PostgreSQL evidence mandatory in production mode.
  - Enforce startup failure when `VRL_DATABASE_URL` is missing outside local development.
  - Remove any ambiguity between "demo mode" and "production mode".
- [ ] Fix the persisted proof schema mismatch.
  - `models/schemas.py` currently stores `ProofRecord.integrity_hash`.
  - `app/db/repository.py` currently writes `proof.final_proof`.
  - Align schema, repository, migrations, and verification logic to one canonical field model.
- [ ] Persist the real ZK evidence bundle, not just the fast-path integrity hash.
  - Store proof bytes or canonical proof payload reference.
  - Store `circuit_hash`.
  - Store `verification_key_hash`.
  - Store verification result and timestamp.
- [ ] Add a real PostgreSQL integration test for the live persistence path.
  - Must cover insert request/result/proof/audit in one transaction.
  - Must verify replay rejection on duplicate input hash.
  - Must verify persisted records can be replay-verified.

## 2. External Verifier Hardening

- [ ] Make `scripts/verify_proof.py` fail safely on malformed bundles.
  - No traceback to user.
  - Always return structured JSON with `valid: false` and a reason.
- [ ] Make `backend/proof_export.py` verification path non-mutating.
  - Do not modify the caller's bundle in place.
  - Work from a copied payload before stripping computed fields.
- [ ] Add adversarial CLI verification tests.
  - Tampered top-level trace hash.
  - Tampered proof metadata.
  - Missing required proof fields.
  - Invalid JSON file.
  - Wrong verification key hash.

## 3. Verified Path API Integrity

- [ ] Fix `/prove` response shape in `api/routes.py`.
  - `circuit_hash` must return the real circuit hash.
  - It must not return `witness_artifact_id`.
- [ ] Add backend readiness preflight before proof jobs are accepted.
  - If native backend is unavailable, reject `/prove` immediately.
  - Do not wait for async queue failure to reveal missing backend.
- [ ] Make proof failure responses explicit and queryable.
  - Keep `input_hash`, `trace_hash`, and queue error reason.
  - Ensure operator can distinguish backend failure vs proof invalidity.

## 4. Audit Chain Integrity

- [ ] Add external audit-chain anchoring.
  - Publish signed chain head snapshots.
  - Or write chain heads to immutable object storage.
  - Or notarize chain heads externally.
- [ ] Add an operator script to verify exported audit records independently.
  - Input: exported audit rows.
  - Output: `VALID` / `INVALID`.
- [ ] Add a live DB test that simulates privileged tampering.
  - Modify `current_hash`.
  - Re-run verification.
  - Confirm chain breaks are detected.

## 5. Reproducibility and Build Integrity

- [ ] Add a hermetic build path.
  - Pin Rust toolchain version explicitly.
  - Document exact native build command.
  - Prefer containerized build for repeatability.
- [ ] Add a reproducible release workflow.
  - Signed Git tag.
  - Build artifact manifest.
  - Binary checksum publication.
- [ ] Promote environment validation to release gate.
  - `scripts/check_environment.py` must pass before smoke/release.
- [ ] Re-run fresh-clone validation from a clean machine or container.
  - Clone repo.
  - Build native backend.
  - Run smoke script.
  - Run external verifier.
  - Confirm same expected hashes and valid proof.

## 6. Performance and SLA Integrity

- [ ] Re-run latency validation on the current code against live PostgreSQL.
  - Replace archived stale metrics with current measurements.
  - Record request p50/p95/p99.
  - Record DB transaction p50/p95/p99.
  - Record proof generation and proof verification timings.
- [ ] Separate latency budgets clearly.
  - Fast path SLA.
  - Verified path SLA.
  - DB-backed persistence SLA.
- [ ] Investigate evidence-layer bottlenecks if p95 exceeds target.
  - Audit-chain lock contention.
  - Transaction round trips.
  - Key loading overhead.

## 7. Terminology and Truth Surface Cleanup

- [ ] Remove ambiguity between integrity artifact and ZK proof.
  - Reserve `proof` for real cryptographic proof objects.
  - Rename fast-path hash artifact if needed.
- [ ] Ensure one canonical externally documented truth model.
  - Fast path = integrity check only.
  - Verified path = cryptographic proof.
  - Evidence layer = append-only forensic record.
- [ ] Update `README.md` and `docs/TRUST_MODEL.md` after fixes land.
  - Do not claim append-only evidence when DB is optional.
  - Do not claim full external verifiability until malformed bundle handling is fixed.

## 8. Test Additions Required Before Production Claim

- [ ] Live PostgreSQL end-to-end test for current repository implementation.
- [ ] CLI malformed-bundle regression tests.
- [ ] `/prove` contract test for correct `circuit_hash`.
- [ ] Missing-backend API rejection test.
- [ ] Proof bundle replay test with changed input.
- [ ] Proof persistence and reload verification test.
- [ ] Fresh-clone reproducibility smoke test.

## 9. Production Readiness Exit Criteria

Mark production integrity as complete only when all are true:

- [ ] DB-backed evidence is mandatory in production.
- [ ] Proof record schema and repository writes are aligned.
- [ ] Real ZK proof bundle is persisted or immutably referenced.
- [ ] Offline verifier returns structured invalid responses for malformed bundles.
- [ ] `/prove` returns correct artifact bindings.
- [ ] Native backend absence is rejected before queue submission.
- [ ] Audit chain is externally anchored.
- [ ] Fresh clone reproduces valid proof verification.
- [ ] Live PostgreSQL validation passes on current code.
- [ ] Documentation matches actual system behavior.

## 10. Recommended Execution Order

1. Fix proof-record schema mismatch.
2. Make DB evidence mandatory in production mode.
3. Harden offline verifier and proof export.
4. Fix `/prove` contract and backend preflight.
5. Persist real ZK proof artifacts.
6. Re-run live PostgreSQL validation.
7. Add external chain anchoring.
8. Lock reproducible build/release workflow.
9. Refresh trust-model and README claims.
