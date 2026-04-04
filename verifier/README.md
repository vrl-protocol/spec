# VRL Standalone Proof Bundle Verifier

A command-line tool for verifying VRL Proof Bundles according to the specification (VRL Spec §12).

## Overview

`vrl_verify.py` is a **standalone verifier** with **zero external dependencies** (uses only Python stdlib: `json`, `hashlib`, `uuid`, `sys`). It implements the complete 10-step verification procedure from VRL Specification §12 and works offline.

## Features

- **No dependencies**: Pure Python stdlib only
- **Offline verification**: Does not require network access for core verification
- **Color-coded output**: Green PASS / Red FAIL for easy visual inspection
- **Verbose mode**: Shows hash values and intermediate computations
- **JSON output**: Machine-readable results for integration
- **Proper exit codes**: 0 (VALID), 1 (INVALID), 2 (ERROR)

## Installation

Copy `vrl_verify.py` to any directory. It requires Python 3.6+.

```bash
chmod +x vrl_verify.py
```

## Usage

### Basic Verification

Verify a bundle from a file:

```bash
python vrl_verify.py bundle.json
```

Verify a bundle from stdin:

```bash
cat bundle.json | python vrl_verify.py
```

### Options

#### `--verbose` / `-v`

Show hash values and intermediate computations for each verification step:

```bash
python vrl_verify.py bundle.json --verbose
```

Output includes computed and expected values for mismatch debugging.

#### `--json-output` / `-j`

Output machine-readable JSON result instead of formatted text:

```bash
python vrl_verify.py bundle.json --json-output
```

Useful for integration with CI/CD pipelines and automated verification.

## Output

### Terminal (Default)

```
VRL Proof Bundle Verifier v1.0
==================================================
Bundle ID:  e2cad545-1910-5f44-a596-1ccd4591c538
AI Model:   vrl-deterministic-engine
Proof:      sha256-deterministic
Circuit:    trade/import-landed-cost@2.0.0

VERIFICATION STEPS
--------------------------------------------------
[PASS] §12.1 Version Check
       vrl_version 1.0 is supported
[PASS] §12.2 Schema Validation
       All required fields present and valid
[PASS] §12.3 bundle_id Recomputation
       bundle_id e2cad545-1910-5f44-a596-1ccd4591c538 is valid
[PASS] §12.4 Integrity Hash Recomputation
       integrity_hash verified
[PASS] §12.5 Circuit Registry Lookup
       Circuit trade/import-landed-cost@2.0.0 verified
[PASS] §12.6 Proof Verification
       Proof structure valid for sha256-deterministic
[PASS] §12.7 AI-ID Verification
       AI-ID format valid (no provider_signature; AI-ID is advisory only)
[PASS] §12.8 Data Commitment Signatures
       All 1 data commitments verified

RESULT: VALID ✓
==================================================
```

### JSON Output

```json
{
  "status": "VALID",
  "bundle_id": "e2cad545-1910-5f44-a596-1ccd4591c538",
  "is_valid": true,
  "errors": [],
  "details": [
    {
      "step": "§12.1 Version Check",
      "status": "PASS",
      "message": "vrl_version 1.0 is supported",
      "error_code": null,
      "computed_value": null,
      "expected_value": null
    }
    ...
  ]
}
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0    | **VALID** or **VALID_PARTIAL** — Core proof passed; optional checks (TSA, graph edges) may have been skipped |
| 1    | **INVALID** — Verification failed (hash mismatch, schema error, missing fields, etc.) |
| 2    | **ERROR** — Input error (file not found, invalid JSON, etc.) |

## Verification Steps (§12)

The verifier performs **10 sequential steps**, each corresponding to a section in VRL Spec §12:

| Step | Name | Checks |
|------|------|--------|
| 1 | Version Check | `vrl_version == "1.0"` |
| 2 | Schema Validation | Required fields, hash format, ai_id format |
| 3 | bundle_id Recomputation | `UUIDv5(VRL_NAMESPACE, integrity_hash)` matches |
| 4 | Integrity Hash Recomputation | `SHA-256(input_hash + output_hash + trace_hash)` matches |
| 5 | Circuit Registry Lookup | Circuit resolves and `circuit_hash` matches |
| 6 | Proof Verification | Proof structure valid; `proof_hash` matches |
| 7 | AI-ID Verification | AI-ID format valid; provider signature (if present) |
| 8 | Data Commitment Signatures | All `commitment_hash` values match |
| 9 | Timestamp Validation | TSA token present (RFC 3161) — **optional** |
| 10 | Proof Graph Edges | Graph dependencies valid — **optional** |

Steps 9 and 10 are optional; if present but verification fails, the result is `VALID_PARTIAL` instead of `INVALID`.

## Examples

### Example 1: Verify a valid trade/import bundle

```bash
$ python vrl_verify.py test_bundles/valid_trade.json

VRL Proof Bundle Verifier v1.0
==================================================
Bundle ID:  e2cad545-1910-5f44-a596-1ccd4591c538
AI Model:   vrl-deterministic-engine
Proof:      sha256-deterministic
Circuit:    trade/import-landed-cost@2.0.0

VERIFICATION STEPS
--------------------------------------------------
[PASS] §12.1 Version Check
       vrl_version 1.0 is supported
[PASS] §12.2 Schema Validation
       All required fields present and valid
[PASS] §12.3 bundle_id Recomputation
       bundle_id e2cad545-1910-5f44-a596-1ccd4591c538 is valid
[PASS] §12.4 Integrity Hash Recomputation
       integrity_hash verified
[PASS] §12.5 Circuit Registry Lookup
       Circuit trade/import-landed-cost@2.0.0 verified
[PASS] §12.6 Proof Verification
       Proof structure valid for sha256-deterministic
[PASS] §12.7 AI-ID Verification
       AI-ID format valid (no provider_signature; AI-ID is advisory only)
[PASS] §12.8 Data Commitment Signatures
       All 1 data commitments verified

RESULT: VALID ✓
==================================================

$ echo $?
0
```

### Example 2: Verify a valid TEE (Intel TDX) bundle

```bash
$ python vrl_verify.py test_bundles/valid_tee.json

VRL Proof Bundle Verifier v1.0
==================================================
Bundle ID:  af99a6af-f130-5bc9-9608-013a2e29c71e
AI Model:   llama-3-70b-instruct
Proof:      tee-intel-tdx
Circuit:    ai/inference-llama@3.0.0

VERIFICATION STEPS
--------------------------------------------------
[PASS] §12.1 Version Check
       vrl_version 1.0 is supported
[PASS] §12.2 Schema Validation
       All required fields present and valid
[PASS] §12.3 bundle_id Recomputation
       bundle_id af99a6af-f130-5bc9-9608-013a2e29c71e is valid
[PASS] §12.4 Integrity Hash Recomputation
       integrity_hash verified
[PASS] §12.5 Circuit Registry Lookup
       Circuit ai/inference-llama@3.0.0 verified
[PASS] §12.6 Proof Verification
       Proof structure valid for tee-intel-tdx
[PASS] §12.7 AI-ID Verification
       AI-ID format valid (no provider_signature; AI-ID is advisory only)
[PASS] §12.8 Data Commitment Signatures
       No data commitments

RESULT: VALID ✓
==================================================

$ echo $?
0
```

### Example 3: Detect tampering

```bash
$ python vrl_verify.py test_bundles/tampered.json

VRL Proof Bundle Verifier v1.0
==================================================
Bundle ID:  00000000-0000-0000-0000-000000000000
AI Model:   vrl-deterministic-engine
Proof:      sha256-deterministic
Circuit:    trade/import-landed-cost@2.0.0

VERIFICATION STEPS
--------------------------------------------------
[PASS] §12.1 Version Check
       vrl_version 1.0 is supported
[PASS] §12.2 Schema Validation
       All required fields present and valid
[FAIL] §12.3 bundle_id Recomputation
       bundle_id mismatch

RESULT: INVALID ✗
==================================================

$ echo $?
1
```

### Example 4: Verbose mode with hash inspection

```bash
$ python vrl_verify.py test_bundles/valid_trade.json --verbose

...
[PASS] §12.3 bundle_id Recomputation
       bundle_id e2cad545-1910-5f44-a596-1ccd4591c538 is valid
       computed: e2cad545-1910-5f44-a596-1ccd4591c538

[PASS] §12.4 Integrity Hash Recomputation
       integrity_hash verified
       computed: 7b58cd2c0b85716175e90136d025d8d282abb1b56cb98ffaa33d4cbde3db70a1

[PASS] §12.5 Circuit Registry Lookup
       Circuit trade/import-landed-cost@2.0.0 verified
       computed: 14414791513f16066b2288ac9053bba1f5de3f4a53f7cb59f1dd68c6ecba58ad
...
```

### Example 5: JSON output for CI/CD

```bash
$ python vrl_verify.py test_bundles/valid_trade.json --json-output | jq '.is_valid'
true

$ python vrl_verify.py test_bundles/tampered.json --json-output | jq '.errors'
["BUNDLE_ID_MISMATCH"]
```

## Test Bundles

Three test bundles are included in `test_bundles/`:

### `valid_trade.json`

- **Type**: Trade/import landed-cost calculation
- **Proof System**: `sha256-deterministic`
- **Status**: Valid — passes all 10 steps
- **Use case**: Demonstrates deterministic computation verification with data commitments (CBP tariff rules)

### `valid_tee.json`

- **Type**: AI inference (Llama-3-70B)
- **Proof System**: `tee-intel-tdx`
- **Status**: Valid — passes all 10 steps
- **Use case**: Demonstrates TEE attestation-based proof without data commitments

### `tampered.json`

- **Type**: Trade/import (same as valid_trade)
- **Proof System**: `sha256-deterministic`
- **Status**: Invalid — fails at step 3 (bundle_id mismatch)
- **Use case**: Demonstrates detection of tampering (integrity_hash has been altered)

## Specification References

- VRL Spec §2: AI Identity Standard (AI-ID)
- VRL Spec §3: Proof Bundle Structure
- VRL Spec §4: Proof Systems
- VRL Spec §5: Circuit Registry
- VRL Spec §6: Data Commitments
- VRL Spec §10: Canonical Serialisation
- VRL Spec §11: Hash Computation
- **VRL Spec §12: Verification Procedure** ← Implemented here

## Limitations

This standalone verifier has the following limitations (by design):

- **No cryptographic proof verification**: ZK proofs (Halo2, Groth16, STARK, zkML) are not fully verified; only structure validation
- **No TEE attestation verification**: TEE reports are not verified against hardware vendor root certificates
- **No provider signature verification**: Ed25519 signatures are not verified against provider public keys
- **No RFC 3161 TSA verification**: Timestamp tokens are not verified against TSA certificate chains
- **No recursive graph verification**: Dependent bundles (proof_graph edges) are not recursively fetched and verified

For full cryptographic verification, integrate this tool with:
- A ZK verification library (e.g., `zk-SNARK` implementations)
- Hardware TEE attestation libraries (e.g., Intel TDX SDK, AMD SEV-SNP tools)
- A TSA client library (e.g., `pyasn1` + RFC 3161)

## Architecture

```
vrl_verify.py (this file)
├── Hashing utilities (§10-11)
│   ├── canonical_json()
│   ├── sha256()
│   ├── compute_integrity_hash()
│   ├── compute_proof_hash()
│   └── compute_commitment_hash()
├── Data classes
│   ├── VerificationStatus (enums)
│   ├── VerificationDetail
│   └── VerificationResult
├── Circuit Registry (mock)
│   └── CircuitRegistry.resolve_circuit()
├── Verifier (main logic)
│   ├── verify()
│   ├── _step1_version_check()
│   ├── _step2_schema_validation()
│   ├── _step3_bundle_id_check()
│   ├── _step4_integrity_hash_check()
│   ├── _step5_circuit_resolution()
│   ├── _step6_proof_structure_validation()
│   ├── _step7_ai_id_verification()
│   ├── _step8_data_commitment_verification()
│   ├── _step9_timestamp_verification()
│   └── _step10_proof_graph_verification()
└── Terminal output formatter
    └── TerminalFormatter.format_result()
```

## Contributing

To extend this verifier:

1. **Add new proof systems**: Update the valid_systems set in `_step6_proof_structure_validation()`
2. **Add cryptographic verification**: Implement full ZK/TEE verification in step 6 (requires external libs)
3. **Add TSA verification**: Implement RFC 3161 verification in step 9
4. **Add graph recursion**: Implement recursive bundle fetching in step 10

## License

This tool is part of the VRL Proof Bundle Specification project, published under CC BY 4.0.

---

**Last Updated**: 2026-04-04
**Spec Version**: VRL v1.0
