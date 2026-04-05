# VRL Open Source Boundary

This document defines what should be public now and what should remain private while VRL is still establishing adoption.

## Open Source Now

The adoption layer should be public immediately.

### Public Repo: `spec`

Open source:

- protocol specification
- standards-facing documentation
- schemas
- example bundles

Representative files:

- `SPEC.md`
- `STRUCTURE.md`
- `VRL_MASTER_PLAN.md`
- `docs/TRUST_MODEL.md`
- `docs/TLS_SETUP.md`
- `registry/schema/circuit.schema.json`
- `verifier/test_bundles/`

Why:

- the spec is the standard-setting layer
- public verification is required for trust
- this does not give away the moat

### Public Repo: `sdk`

Open source:

- `sdk/python/`
- `sdk/typescript/`
- `sdk/go/`
- public example bundles used for tests and docs

Why:

- SDK adoption drives ecosystem growth
- client libraries are not the moat

### Public Repo: `registry`

Open source:

- `registry/registry.json`
- `registry/circuits/`
- `registry/schema/`
- `registry/tools/lookup.py`
- `registry/SUBMISSION.md`

Why:

- the ecosystem needs a visible circuit catalog
- public governance builds trust

### Public Component: Reference Verifier

Open source:

- `verifier/vrl_verify.py`
- `verifier/README.md`
- public example bundles

Why:

- a standard without offline verification is weak
- third parties must be able to verify without asking VRL for permission

## Keep Private For Now

The moat layer should stay private until adoption exists.

### Private Repo: `server`

Keep private:

- `app/`
- `api/`
- `backend/`
- `infra/`

Why:

- this is the operational trust layer
- managed execution, uptime, enforcement, and integrations are monetizable

### Private Orchestration Layer

Keep private:

- `agents/`
- `coordinator/`
- `orchestrator.py`
- `memory/`

Why:

- this is part of the internal circuit-factory and execution orchestration moat

### Private ZK Runtime Internals

Keep private initially:

- `zk/provers/`
- `zk/verifiers/plonk_verifier.py`
- `zk/rust_bridge.py`
- `zk/rust_backend/`
- `zk/keys/`

Why:

- the runtime packaging and operational proving path are part of the moat
- generated key material should never be public

### Private Enterprise Controls

Keep private:

- `security/`
- operational audit controls
- API key enforcement
- enterprise-specific integrations

Why:

- these are commercial infrastructure features

## Open Later

These can move from private to public once the public repos have traction:

- `core/`
- `models/`
- `utils/`
- selected `tests/`
- basic `ui/`

Why:

- they help community trust and contributions
- they are not necessary for initial adoption

## Never Publish

Do not publish:

- `logs/`
- `zk/keys/`
- `zk/rust_backend/target/`
- `.env`
- `.env.*`
- local cache directories
- accidental machine-local history or secrets

## Practical Rule

Open source the protocol layer now.

Keep the operational trust network, execution layer, governance enforcement, and enterprise integrations private until the ecosystem starts using the standard.
