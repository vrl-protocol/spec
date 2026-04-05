# VRL Repository Split Plan

This repository is a transitional monorepo. The target state is four public repositories under `vrl-protocol`:

1. `spec`
2. `sdk`
3. `registry`
4. `server`

The goal of the split is to give each repository a single responsibility:

- `spec`: protocol definition, schemas, example bundles, and standards documentation
- `sdk`: installable developer libraries in Python, TypeScript, and Go
- `registry`: circuit metadata, governance, certification, and validation
- `server`: executable reference implementation, API, proving backend, verifier backend, UI, and tests

## Current State

The current repo contains all four concerns:

- protocol and standards documents
- language SDKs
- circuit registry
- backend, ZK prover/verifier, API, UI, and operational code

This works for rapid solo iteration, but it blurs release boundaries and makes the `spec` repository name misleading.

## Target Mapping

### 1. `vrl-protocol/spec`

Move:

- `README.md`
- `SPEC.md`
- `STRUCTURE.md`
- `VRL_MASTER_PLAN.md`
- `docs/TRUST_MODEL.md`
- `docs/TLS_SETUP.md`
- `registry/schema/circuit.schema.json`
- `verifier/test_bundles/`

Keep the repo focused on:

- proof bundle standard
- schemas
- normative examples
- protocol changelog

Do not keep runtime code here.

### 2. `vrl-protocol/sdk`

Move:

- `sdk/python/`
- `sdk/typescript/`
- `sdk/go/`

Also copy:

- `verifier/test_bundles/` as shared test vectors

Keep the repo focused on:

- installable SDKs
- package publishing
- language-specific CI
- shared test fixtures

### 3. `vrl-protocol/registry`

Move:

- `registry/README.md`
- `registry/SUBMISSION.md`
- `registry/registry.json`
- `registry/circuits/`
- `registry/schema/`
- `registry/tools/lookup.py`
- `.github/scripts/validate_registry.py`

Keep the repo focused on:

- circuit catalog
- certification status
- governance and submissions
- registry validation

### 4. `vrl-protocol/server`

Move:

- `agents/`
- `api/`
- `app/`
- `backend/`
- `coordinator/`
- `core/`
- `infra/`
- `memory/`
- `migrations/`
- `models/`
- `scripts/`
- `security/`
- `src/`
- `tests/`
- `ui/`
- `utils/`
- `verifier/vrl_verify.py`
- `zk/`
- `orchestrator.py`
- `pytest.ini`
- `requirements.txt`

Keep the repo focused on:

- reference server
- proof generation
- proof verification
- API/UI
- ZK backend
- integration and operational tests

## Files That Should Not Move As-Is

These are generated or environment-specific and should not be copied into the new repos:

- `.pytest_cache/`
- `.ruff_cache/`
- `logs/`
- `zk/keys/`
- `zk/rust_backend/target/`
- `.env`
- `.env.*`

## Migration Order

Recommended order:

1. Split `spec`
2. Split `sdk`
3. Split `registry`
4. Split `server`
5. Freeze this monorepo as a temporary integration workspace or archive it

This order keeps the protocol definition stable first, then the developer surface, then the governance layer, then the full runtime.

## Recommended Release Boundaries

### `spec`

- semantic versions for the protocol
- slow, deliberate releases

### `sdk`

- independent language package releases
- frequent releases

### `registry`

- append-only circuit metadata changes
- signed registry snapshots later

### `server`

- application releases
- infrastructure and runtime changes

## Transitional Recommendation

Keep this repo as the local integration workspace until the split is complete. Use the export script and manifest in this repo to generate the four target repositories repeatedly while boundaries are still changing.
