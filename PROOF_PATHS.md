# VRL Proof Paths

VRL currently has two concrete implementation paths that are useful for different reasons:

- the public SDK path, which makes it easy to build and verify a spec-shaped bundle locally
- the server/reference path, which exercises the fuller proof pipeline, artifact export, and determinism checks

Both produce VRL bundles. They do not provide the same assurance level.

## SDK Path

Repository:
- `https://github.com/vrl-protocol/sdk`

Primary demo:

```bash
cd sdk/python
python examples/build_and_verify.py
```

What it does:
- constructs a VRL bundle using the public Python SDK
- computes `ai_id`, `input_hash`, `output_hash`, `trace_hash`, `integrity_hash`, and `proof_hash`
- writes `examples/sdk_demo_bundle.json`
- verifies the bundle locally with `Verifier()`

What it proves:
- the bundle shape matches the public SDK and verifier contract
- hashing, identity, and local offline verification work end to end
- a developer can adopt VRL quickly from `pip install vrl-sdk`

Current assurance mode:
- `sha256-deterministic`

What this does not claim:
- a hardware-rooted attestation
- a general proof that an external provider actually ran a claimed model
- the stronger server-side proof export path

## Server Path

Repository:
- `https://github.com/vrl-protocol/server`

Primary demo:

```bash
python scripts/smoke_e2e.py
python scripts/verify_proof.py logs/smoke_proof_bundle.json
```

What it does:
- runs the reference proof pipeline from request to exported bundle
- writes `logs/smoke_proof_bundle.json`
- verifies the exported bundle offline
- checks repeated-run determinism for `input_hash`, `output_hash`, `trace_hash`, `circuit_hash`, `verification_key_hash`, `proof_blob_hex`, and `final_proof`

What it proves:
- the reference server path can generate a reproducible artifact
- the exported bundle can be validated offline
- the proof backend, export flow, and verifier surface line up

Current assurance mode:
- reference server proof pipeline with PLONK-backed proving components plus deterministic artifact checks

What this still does not claim:
- production TEE attestation for a live hosted model
- a universal proof for every possible AI workload
- that all proof systems listed in the spec are equally mature in implementation

## Practical Difference

The SDK path is the easiest way to adopt VRL:
- fastest install
- simplest demo
- best for learning the bundle format and local verification flow

The server path is the strongest current proof of concept:
- fuller proof/export pipeline
- offline verification of emitted artifacts
- repeated-run determinism checks

In short:
- use the SDK path to learn and integrate VRL
- use the server path to evaluate the stronger reference proof flow

## Today vs. Direction

VRL is designed as one bundle format that can carry multiple assurance levels:
- hash-binding or deterministic hashing for low-friction adoption
- TEE attestation for hardware-rooted execution claims
- ZK proofs for stronger cryptographic correctness claims

The current public proof of concept shows the first and third categories in different ways:
- the SDK demonstrates the bundle and verifier surface cleanly
- the server demonstrates the deeper proof/export pipeline and reproducibility

That distinction is intentional. The goal is one portable verification envelope, not the claim that every VRL bundle carries identical proof strength.
