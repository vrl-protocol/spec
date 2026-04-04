# VRL Circuit Registry

The VRL Circuit Registry is the authoritative catalog of all registered verifiable circuits in the Verifiable Reality Layer ecosystem. It provides human-readable identifiers, cryptographic hashes, and complete descriptors for circuits used in proof bundles.

## Overview

A **circuit** is a deterministic, verifiable computation encoded as a set of arithmetic constraints. Each circuit is identified by:

- **circuit_id**: Human-readable name in format `<domain>/<name>@<version>` (e.g., `trade/import-landed-cost@2.0.0`)
- **circuit_hash**: The immutable SHA-256 digest of the circuit's canonical descriptor

The registry serves as the single source of truth for circuit validation. When a verifier sees a proof bundle referencing a circuit, they look up the circuit in this registry, retrieve its full descriptor, recompute the `circuit_hash`, and verify it matches the hash claimed in the proof bundle.

## Circuit Domains

Circuits are organized by domain:

- **trade**: International trade, tariffs, landed costs, export compliance
- **healthcare**: Clinical decision support, diagnostic reasoning, treatment protocols
- **finance**: Credit risk, fraud detection, financial modeling
- **general**: Infrastructure circuits (TEE attestation, API binding, hash computation)

## Certification Tiers

Every registered circuit is assigned a certification tier reflecting the level of review and assurance:

### EXPERIMENTAL

- **Status**: Community submitted, minimal validation
- **Requirements**:
  - Passes automated constraint syntax checks
  - Circuit descriptor conforms to JSON schema
  - No known security flaws identified in code review
- **Use Case**: Development, testing, academic research
- **Assurance Level**: Low — suitable for non-critical, exploratory work only
- **Approval**: Auto-approved by registry upon valid submission

### REVIEWED

- **Status**: Formally reviewed by VRL maintainers
- **Requirements**:
  - Passes all EXPERIMENTAL requirements
  - Code review completed by at least 2 VRL maintainers
  - Security audit for cryptographic soundness
  - Documentation is complete and accurate
  - Test coverage >= 80% for constraint logic
- **Use Case**: Production use in non-regulated contexts, internal business logic
- **Assurance Level**: Medium — trusted by VRL maintainers but not independently audited
- **Approval**: Requires 2 maintainer sign-offs and a 7-day public review window

### CERTIFIED

- **Status**: Independently audited and formally verified
- **Requirements**:
  - Passes all REVIEWED requirements
  - Third-party security audit (e.g., by Trail of Bits, OpenZeppelin, Least Authority)
  - Formal verification of constraint system (where applicable)
  - Regulatory pre-approval for target jurisdiction (if applicable)
  - Proof system strength audit (e.g., cryptanalysis of proof system parameters)
- **Use Case**: Regulated industries (healthcare, finance), legal evidence, critical infrastructure
- **Assurance Level**: High — formally verified and independently audited
- **Approval**: Requires independent audit report + VRL maintainer sign-off

## Registry Structure

```
registry/
├── README.md                    # This file
├── registry.json                # Master registry (index of all circuits)
├── SUBMISSION.md                # How to submit a new circuit
├── circuits/                    # Individual circuit descriptors
│   ├── trade-import-landed-cost-1.0.0.json
│   ├── trade-import-landed-cost-2.0.0.json
│   ├── trade-export-compliance-check-1.0.0.json
│   ├── healthcare-clinical-decision-support-1.0.0.json
│   ├── finance-credit-risk-scoring-1.0.0.json
│   ├── finance-fraud-detection-1.0.0.json
│   ├── general-tee-inference-attestation-1.0.0.json
│   └── general-api-hash-binding-1.0.0.json
├── schema/
│   └── circuit.schema.json      # JSON schema for circuit validation
└── tools/
    └── lookup.py                # CLI tool for querying the registry
```

## Looking Up a Circuit

### Using the CLI Tool

The registry includes a Python CLI tool for querying circuits:

```bash
# Look up a specific circuit
python tools/lookup.py trade/import-landed-cost@2.0.0

# List all circuits
python tools/lookup.py --list

# Filter by domain
python tools/lookup.py --list --domain trade

# Filter by domain and certification tier
python tools/lookup.py --list --domain finance --tier CERTIFIED
```

### Using the registry.json

Load the master registry file and search by `circuit_id`:

```json
{
  "circuits": [
    {
      "circuit_id": "trade/import-landed-cost@2.0.0",
      "circuit_hash": "a1b2c3d4...",
      "certification_tier": "REVIEWED",
      ...
    }
  ]
}
```

### Programmatic Access

Any client can:

1. Fetch the `registry.json` file
2. Search for the circuit by `circuit_id`
3. Retrieve the full descriptor from `circuits/<circuit_slug>.json`
4. Recompute the `circuit_hash` to verify integrity
5. Check the `certification_tier` against your trust requirements

## Submitting a Circuit

See [SUBMISSION.md](./SUBMISSION.md) for the full submission process, including:

- How to write a circuit descriptor
- How to compute the circuit hash
- The PR template and review criteria
- How to prepare for different certification tiers

## Circuit Descriptor Schema

Every circuit must conform to the JSON schema defined in `schema/circuit.schema.json`. The descriptor includes:

- **circuit_id**: Human-readable identifier
- **spec_version**: VRL spec version (currently "vrl/circuit/1.0")
- **circuit_hash**: SHA-256 of canonical descriptor
- **domain**: Logical grouping (trade, healthcare, finance, general)
- **name**: Short name of the circuit
- **version**: Semantic version
- **description**: Human-readable description
- **input_schema**: Definition of private and public inputs
- **output_schema**: Definition of public outputs
- **proof_systems**: Array of supported proof systems
- **constraint_count**: Number of arithmetic constraints
- **dataset_dependencies**: External datasets required
- **author**: Circuit author(s)
- **license**: Open-source license identifier
- **published_at**: ISO 8601 timestamp of publication
- **certification_tier**: EXPERIMENTAL, REVIEWED, or CERTIFIED

## Immutability and Versioning

**Circuit Hash Immutability**: Once a circuit is published with a given `circuit_hash`, that hash is permanent and immutable. The constraints, input/output schema, and dependencies are forever fixed for that circuit version.

**Versioning**: Changes to a circuit (bug fixes, performance improvements, constraint changes) require bumping the semantic version number, which produces a new `circuit_hash`. Both versions coexist in the registry.

**No Retractions**: Circuits are never deleted from the registry. If a circuit is found to be insecure or non-functional, it is marked `deprecated: true` but remains in the registry for forensic purposes (to verify old proof bundles that reference it).

## Trust Model

The registry uses a multi-tier trust model:

- **Verifier chooses their trust level**: Each verifier decides what certification tier they require based on their risk tolerance and regulatory context.
- **Transparent audit trail**: All submissions, reviews, and audits are tracked in the git history.
- **Cryptographic binding**: The circuit_hash cryptographically binds the circuit descriptor to all proof bundles that reference it.
- **Independent verification**: Verifiers can recompute the circuit_hash themselves using any implementation of SHA-256.

## API Compatibility

The registry JSON is designed to be compatible with:

- npm registry API (similar structure)
- Maven Central Repository
- IANA registries
- Crates.io (Rust package registry)

Third-party tooling and integrations can expect:

- Stable JSON schema
- Deterministic circuit_hash computation
- Immutable once published
- Versioned updates

## Registry Metadata

- **Last Updated**: 2026-04-04
- **Registry Version**: 1.0.0
- **Total Circuits**: 8 (8 unique circuit_ids)
- **Domains Covered**: 4 (trade, healthcare, finance, general)
- **Certification Distribution**:
  - EXPERIMENTAL: 0
  - REVIEWED: 7
  - CERTIFIED: 1

## License

The VRL Circuit Registry specification and all circuit descriptors are licensed under CC BY 4.0. Individual circuits may have their own licenses as specified in their descriptor.

---

**Registry Maintainers**: VRL Contributors
**Repository**: https://github.com/vrl-protocol/spec
**Issues**: https://github.com/vrl-protocol/spec/issues
**Discussions**: https://github.com/vrl-protocol/spec/discussions
