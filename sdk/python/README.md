# VRL SDK - Verifiable Reality Layer Python SDK

A complete, production-ready Python implementation of the [VRL Proof Bundle Specification v1.0](https://github.com/vrl-protocol/spec).

The VRL SDK provides cryptographically verifiable attestation for AI model outputs and deterministic computations, enabling third parties to independently verify authenticity without trusting the issuing party.

## Features

- **ProofBundle**: Complete implementation of VRL Proof Bundle structure (§3)
- **Verifier**: Full 10-step verification procedure per VRL Spec §12
- **Canonical JSON**: Spec-compliant hash computation with sorted keys and no whitespace (§10)
- **SHA-256 Hashing**: All hash functions use SHA-256 as specified (§11)
- **AI Identity**: AI-ID computation with provider signature support (§2)
- **Fluent Builders**: Easy-to-use builder APIs for constructing bundles
- **Multiple Proof Systems**: Support for all proof systems defined in spec (§4)
  - `plonk-halo2-pasta`, `plonk-halo2-bn254`
  - `groth16-bn254`, `stark`, `zk-ml`
  - `tee-intel-tdx`, `tee-amd-sev-snp`, `tee-aws-nitro`
  - `sha256-deterministic`, `api-hash-binding`
- **Data Commitments**: External dataset binding with provider signatures (§6)
- **Legal Metadata**: Jurisdiction, compliance, and timestamp authority support (§8)
- **Proof Graphs**: Causal dependency tracking for composite proofs (§7)

## Installation

### From PyPI

```bash
pip install vrl-sdk
```

### From source

```bash
git clone https://github.com/vrl-protocol/sdk.git
cd sdk/sdk/python
pip install -e .
```

## Quick Start

### Creating a Simple Bundle

```python
from vrl import (
    ProofBundleBuilder, ComputationBuilder, ProofBuilder,
    AIIdentity, Proof, Computation
)
from datetime import datetime, timezone

# 1. Create an AI identity
ai_identity = AIIdentity(
    ai_id="a3f2c1d4e5b6a7f8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1",
    model_name="gpt-4-turbo",
    model_version="2024-04-09",
    provider_id="com.openai",
    execution_environment="api-attested"
)

# 2. Create a computation record
computation = (ComputationBuilder()
    .set_circuit_id("trade/import-landed-cost@2.0.0")
    .set_circuit_version("2.0.0")
    .set_circuit_hash("3fa24c7763608b01b4c7e411655ebc75ff7a906c38bd79a4cc3be0f4479cdf23")
    .set_input_hash("ebf1f0aa67d10b8472fd7f1af22fc9370ecb813243f928b4f5528ab27457fea7")
    .set_output_hash("0c866369e1ab87b0d0b624c0fdeb490aa05fa2524e9368a023308a1437ec5b5b")
    .set_trace_hash("e14d0cb8d4a11cf1db1def3942fa7246b72cb6989463e8d379ade6e90a0405e6")
    .compute_integrity_hash()
    .build())

# 3. Create a proof
proof = (ProofBuilder()
    .set_proof_system("sha256-deterministic")
    .set_proof_bytes("0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d")
    .set_public_inputs([])
    .set_verification_key_id("aadfa62983a64cb674b1b9b1c4379d8a01e02948fed731506de4bcf2950012a0")
    .build())

# Note: proof_hash must be computed separately after proof creation
from vrl import compute_proof_hash
proof.proof_hash = compute_proof_hash(
    computation.circuit_hash,
    proof.proof_bytes,
    proof.public_inputs,
    proof.proof_system,
    computation.trace_hash
)

# 4. Build the bundle
bundle = (ProofBundleBuilder()
    .set_ai_identity(ai_identity)
    .set_computation(computation)
    .set_proof(proof)
    .set_issued_at_now()
    .build())

print(f"Created bundle: {bundle.bundle_id}")
print(bundle.to_json(pretty=True))
```

### Verifying a Bundle

```python
from vrl import Verifier, ProofBundle
import json

# Load a bundle from JSON
with open("bundle.json") as f:
    bundle_data = json.load(f)
bundle = ProofBundle.from_dict(bundle_data)

# Verify it
verifier = Verifier()
result = verifier.verify(bundle)

print(f"Verification status: {result.status}")
print(f"Is valid: {result.is_valid}")
print(f"Errors: {result.errors}")

# Inspect detailed results
for detail in result.details:
    print(f"  {detail.step}: {detail.status} - {detail.message}")
```

### Computing Hashes

```python
from vrl import (
    sha256, canonical_json,
    compute_input_hash, compute_output_hash, compute_trace_hash,
    compute_integrity_hash, compute_ai_id
)

# Canonical JSON
obj = {"z": 1, "a": "hello", "m": [3, 1, 2]}
canonical = canonical_json(obj)
print(canonical)  # {"a":"hello","m":[3,1,2],"z":1}

# SHA-256
hash_value = sha256(canonical)
print(hash_value)  # lowercase 64-char hex

# Compute integrity hash from component hashes
integrity = compute_integrity_hash(
    input_hash="ebf1f0aa67d10b8472fd7f1af22fc9370ecb813243f928b4f5528ab27457fea7",
    output_hash="0c866369e1ab87b0d0b624c0fdeb490aa05fa2524e9368a023308a1437ec5b5b",
    trace_hash="e14d0cb8d4a11cf1db1def3942fa7246b72cb6989463e8d379ade6e90a0405e6"
)

# Compute AI-ID
ai_id = compute_ai_id(
    model_weights_hash="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2",
    runtime_hash="b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3",
    config_hash="c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4",
    provider_id="com.openai",
    model_name="gpt-4-turbo",
    model_version="2024-04-09"
)
```

### Working with Data Commitments

```python
from vrl import DataCommitment, compute_commitment_hash

# Create a data commitment
commitment = DataCommitment(
    dataset_id="cbp/hts-tariff-rules",
    dataset_version="2026.1.0",
    dataset_hash="d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5",
    provider_id="gov.us.cbp",
    committed_at="2026-04-01T00:00:00.000Z",
    commitment_hash=compute_commitment_hash(
        dataset_id="cbp/hts-tariff-rules",
        dataset_version="2026.1.0",
        dataset_hash="d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5",
        provider_id="gov.us.cbp",
        committed_at="2026-04-01T00:00:00.000Z"
    )
)

# Add to bundle
bundle = (ProofBundleBuilder()
    .set_ai_identity(ai_identity)
    .set_computation(computation)
    .set_proof(proof)
    .add_data_commitment(commitment)
    .set_issued_at_now()
    .build())
```

## Core Concepts

### ProofBundle

The top-level container for a VRL proof bundle. Contains:

- **vrl_version**: Specification version ("1.0")
- **bundle_id**: Deterministic UUIDv5 from integrity_hash
- **issued_at**: RFC 3339 timestamp
- **ai_identity**: AI model identity claim
- **computation**: Hashed computation artefacts
- **proof**: Cryptographic proof or attestation
- **data_commitments**: Optional external dataset bindings
- **legal**: Optional legal/compliance metadata
- **proof_graph**: Optional causal dependency graph
- **trust_context**: Optional trust score and anomaly flags

### Verification (§12)

The Verifier implements the 10-step procedure:

1. **Version Check**: Verify `vrl_version == "1.0"`
2. **Schema Validation**: Validate against JSON Schema
3. **bundle_id Recomputation**: UUIDv5(VRL_NAMESPACE, integrity_hash)
4. **Integrity Hash Recomputation**: SHA-256(input_hash + output_hash + trace_hash)
5. **Circuit Resolution**: Verify circuit exists and hash matches
6. **Proof Verification**: Validate proof structure and recompute proof_hash
7. **AI-ID Verification**: Verify AI-ID recomputation (if provider_signature present)
8. **Data Commitment Verification**: Verify each commitment hash
9. **Timestamp Verification**: Validate RFC 3161 TSA token (optional, network)
10. **Proof Graph Edges**: Recursively verify dependencies (optional, network)

### Canonical JSON (§10)

All hashing uses canonical JSON with:

- Lexicographically sorted keys
- No whitespace
- Strings as UTF-8 with lowercase unicode escapes
- Numbers/booleans/null as-is

Example:

```python
from vrl import canonical_json

obj = {"z": 1, "a": "hello", "m": [3, 1, 2]}
canonical = canonical_json(obj)
# Result: {"a":"hello","m":[3,1,2],"z":1}
```

### Hash Computation (§11)

All hashes use SHA-256 producing lowercase 64-character hex strings:

```python
from vrl import sha256, compute_integrity_hash

# Direct hash
hash1 = sha256("some data")

# Integrity hash: SHA-256(input_hash + output_hash + trace_hash)
integrity = compute_integrity_hash(
    input_hash="...",
    output_hash="...",
    trace_hash="..."
)
```

## API Reference

### Classes

- **ProofBundle**: Main proof bundle container
- **Computation**: Computation record with hashes
- **Proof**: Cryptographic proof
- **AIIdentity**: AI model identity claim
- **DataCommitment**: External dataset binding
- **Legal**: Legal metadata and compliance claims
- **ProofGraph**: Causal dependency graph
- **TrustContext**: Trust score and anomaly data
- **Verifier**: Bundle verification engine
- **VerificationResult**: Verification result with details

### Builders

- **ProofBundleBuilder**: Fluent builder for bundles
- **ComputationBuilder**: Fluent builder for computation records
- **ProofBuilder**: Fluent builder for proofs
- **AIIdentityBuilder**: Fluent builder for AI identities

### Hash Functions

- `sha256(data: str) -> str`: SHA-256 hash
- `canonical_json(obj: Any) -> str`: Canonical JSON serialization
- `compute_ai_id(...)`: AI-ID computation per §2.2
- `compute_integrity_hash(...)`: Integrity hash per §11.4
- `compute_proof_hash(...)`: Proof hash per §11.5
- `compute_input_hash(...)`: Input hash per §11.1
- `compute_output_hash(...)`: Output hash per §11.2
- `compute_trace_hash(...)`: Trace hash per §11.3
- `compute_commitment_hash(...)`: Commitment hash per §6.2

## Proof Systems

Supported proof systems per VRL Spec §4:

| System | Description |
|--------|-------------|
| `plonk-halo2-pasta` | PLONK via Halo2 on Pasta curve |
| `plonk-halo2-bn254` | PLONK via Halo2 on BN254 curve |
| `groth16-bn254` | Groth16 on BN254 curve |
| `stark` | STARKs (transparent, post-quantum) |
| `zk-ml` | zkML via EZKL |
| `tee-intel-tdx` | Intel TDX hardware attestation |
| `tee-amd-sev-snp` | AMD SEV-SNP hardware attestation |
| `tee-aws-nitro` | AWS Nitro Enclave attestation |
| `sha256-deterministic` | SHA-256 hash chain (deterministic only) |
| `api-hash-binding` | HMAC-SHA256 input/output binding |

## Error Codes

Verification can return these error codes:

- `SCHEMA_INVALID`: Bundle doesn't conform to spec
- `BUNDLE_ID_MISMATCH`: Computed bundle_id doesn't match
- `INTEGRITY_MISMATCH`: Integrity hash doesn't match
- `CIRCUIT_HASH_MISMATCH`: Circuit hash doesn't match registry
- `PROOF_INVALID`: Proof verification failed
- `TEE_ATTESTATION_INVALID`: TEE attestation invalid
- `RECOMPUTATION_MISMATCH`: Deterministic recomputation mismatch
- `HASH_BINDING_INVALID`: HMAC-SHA256 binding failed
- `AI_ID_INVALID`: AI-ID recomputation failed
- `DATA_COMMITMENT_INVALID`: Data commitment hash failed
- `TIMESTAMP_INVALID`: RFC 3161 token invalid
- `GRAPH_EDGE_INVALID`: Dependency bundle verification failed
- `UNSUPPORTED_VERSION`: VRL version not supported

## Development

### Testing

```bash
pip install -e ".[dev]"
pytest tests/
pytest --cov=vrl tests/
```

## End-To-End SDK Demo

Build a VRL bundle with the public Python SDK and verify it locally:

```bash
cd sdk/python
python examples/build_and_verify.py
```

This writes `examples/sdk_demo_bundle.json` and prints a summary containing:
- `bundle_id`
- `ai_id`
- `integrity_hash`
- `proof_hash`
- verification status

### Code Style

```bash
black vrl/ tests/
flake8 vrl/ tests/
mypy vrl/
```

## Specification Reference

This SDK implements [VRL Proof Bundle Specification v1.0](https://github.com/vrl-protocol/spec):

- §2: AI Identity Standard (AI-ID)
- §3: Proof Bundle Structure
- §4: Proof Systems
- §6: Data Commitments
- §7: Proof Graph
- §8: Legal Layer
- §10: Canonical Serialisation
- §11: Hash Computation
- §12: Verification Procedure

## License

This SDK is licensed under CC BY 4.0, same as the VRL specification.

See [VRL Protocol](https://github.com/vrl-protocol/spec) for more information.
