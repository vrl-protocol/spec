# VRL

Open standard for cryptographically verifiable AI outputs.

VRL defines a portable proof bundle format that lets any third party verify an AI output or deterministic computation offline, without trusting the issuer or any central server.

Think of it as a standard receipt for AI:
- which model or system ran
- what it computed
- what data commitments it depended on
- what proof system attests to correctness
- when the result was issued

## Why This Exists

Today, most AI outputs are plain text with no durable proof of provenance. In regulated settings like healthcare, finance, trade, and legal workflows, that is not enough.

VRL is designed to make AI outputs:
- verifiable
- portable
- tamper-evident
- auditable
- usable across organizations and jurisdictions

## Repositories

The VRL organization is split by responsibility:

- `vrl-protocol/spec`: specification, schemas, and standards-facing docs
- `vrl-protocol/sdk`: Python, TypeScript, and Go SDKs
- `vrl-protocol/registry`: circuit catalog and submission flow
- `vrl-protocol/server`: prover, attestation, and runtime components

## Start Here

- Specification: [SPEC.md](./SPEC.md)
- Proof path comparison: [PROOF_PATHS.md](./PROOF_PATHS.md)
- Live docs and browser verifier: `https://vrl-protocol.github.io/spec/`
- Python package: `pip install vrl-sdk`
- SDK repo: `https://github.com/vrl-protocol/sdk`
- Registry repo: `https://github.com/vrl-protocol/registry`

## What A VRL Bundle Contains

A proof bundle can include:
- AI identity metadata
- computation hashes for inputs, outputs, and trace
- a proof record for ZK, TEE, or hash-binding modes
- dataset commitments
- legal and compliance metadata
- graph links to upstream or downstream proofs

## Proof Systems

VRL is proof-system agnostic. Current modes include:
- `plonk-halo2-pasta`
- `tee-intel-tdx`
- `tee-amd-sev-snp`
- `zk-ml`
- `sha256-deterministic`
- `api-hash-binding`

## Quick Links

- Spec release history: `https://github.com/vrl-protocol/spec/releases`
- SDK release history: `https://github.com/vrl-protocol/sdk/releases`
- PyPI package: `https://pypi.org/project/vrl-sdk/`

## Proof Of Concept Status

Current implementation surfaces that have been exercised end to end:
- Python SDK test suite: 31 passing tests
- TypeScript SDK test suite: 6 passing tests
- Standalone server/reference implementation: 97 passing tests
- Published Python package: `vrl-sdk==0.2.1`

These cover bundle construction, offline verification, proof export, deterministic reference flows, and the reference server proof pipeline.

Reference demo flow:
- `https://github.com/vrl-protocol/server`
- `python scripts/smoke_e2e.py`
- `python scripts/verify_proof.py logs/smoke_proof_bundle.json`

SDK demo flow:
- `https://github.com/vrl-protocol/sdk`
- `python examples/build_and_verify.py`

For a direct comparison of what each path proves today, see [PROOF_PATHS.md](./PROOF_PATHS.md).

## License

The specification is licensed under CC BY 4.0. SDK and implementation code use MIT unless stated otherwise.
