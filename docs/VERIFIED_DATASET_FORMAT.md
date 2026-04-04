# Verified Dataset Format

The canonical training artifact for Verifiable Reality Layer is a
`VerifiedTrainingRecord`.

Source of truth:
- [models/verified_dataset.py](C:/Users/13173/OneDrive/Documents/verifiable-reality-layer/models/verified_dataset.py)
- [backend/verified_dataset.py](C:/Users/13173/OneDrive/Documents/verifiable-reality-layer/backend/verified_dataset.py)

Rules:
- only proof-verified outputs may be converted into a training record
- every record binds:
  - `input_hash`
  - `output_hash`
  - `trace_hash`
  - `witness_hash`
  - `integrity_hash`
  - `final_proof`
  - `circuit_hash`
  - `verification_key_hash`
- every record includes the canonical input payload, result payload, trace, and proof bundle

Version:
- `verified-training-record-v1`

This record format exists so agents can train only on verified truth and so
historical computations can be replayed and audited without relying on hidden
runtime state.
