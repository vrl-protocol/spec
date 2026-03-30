# Trust Model

## What Is Trusted
- The local source tree under `verifiable-reality-layer`
- The deterministic Python calculation engine
- The compiled native Halo2 backend binary at `zk/rust_backend/target/release`
- The canonical serialization and hashing utilities

## What Is Verified
- Input canonicalization and schema validation
- Deterministic trace generation from input
- Deterministic witness derivation from trace and output
- Circuit identity through `circuit_hash`
- Verification key identity through `verification_key_hash`
- Proof validity through the native Halo2 verifier

## What Is Cryptographically Proven
- The exported proof binds to:
  - `trace_hash`
  - `circuit_hash`
  - canonical public inputs
- The verifier rejects:
  - modified trace bindings
  - modified circuit bindings
  - modified verification-key bindings
  - tampered proof bytes

## What Is Not Trusted
- External callers
- Environment variables beyond explicit configuration
- Database state for standalone bundle verification
- In-memory runtime state

## Third-Party Validation Flow
1. Obtain a proof bundle exported by the system.
2. Run `python scripts/verify_proof.py proof_bundle.json`.
3. The verifier:
   - rebuilds the deterministic trace and witness from the bundled input
   - recompiles or re-derives the deterministic circuit/key material
   - checks `input_hash`, `trace_hash`, `circuit_hash`, and `verification_key_hash`
   - verifies the proof through the native Halo2 backend
4. If all checks pass, the bundle is externally valid.

## Failure Model
- Proof failures are logged to `logs/proof_failures.jsonl`
- Failures are linked to `input_hash` and `trace_hash`
- There is no silent retry path in the verified proof pipeline

