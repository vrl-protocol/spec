# VRL Go SDK

A complete Go SDK for the Verifiable Reality Layer (VRL) proof bundle specification. Build, serialize, and verify cryptographic proof bundles that attest to the identity, inputs, outputs, and execution correctness of AI systems and deterministic computations.

## Features

- **Zero external dependencies** — Uses only Go stdlib (`crypto/sha256`, `encoding/json`, `sort`, etc.)
- **Full VRL v1.0 spec compliance** — Implements all required types, hashing functions, and verification steps
- **Builder pattern** — Fluent API for constructing valid proof bundles with automatic hash computation
- **Cryptographic verification** — Complete verification procedure per spec §12 with detailed error reporting
- **Canonical JSON** — Implements spec §10 canonical serialization with sorted keys
- **CLI tool** — `vrl-verify` for command-line bundle verification

## Installation

```bash
go get github.com/vrl-protocol/spec/sdk/go
```

## Quick Start

### Building a Proof Bundle

```go
package main

import (
	"fmt"
	"github.com/vrl-protocol/spec/sdk/go/vrl"
)

func main() {
	// Create a builder
	builder := vrl.NewBuilder()

	// Set AI identity
	aiParams := vrl.AIIdentityParams{
		AIID:                 "a3f2c1d4e5b6a7f8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a",
		ModelName:            "my-model",
		ModelVersion:         "1.0.0",
		ProviderID:           "io.example",
		ExecutionEnvironment: "deterministic",
	}

	// Set computation details
	compParams := vrl.ComputationParams{
		CircuitID:      "trade/import-landed-cost@2.0.0",
		CircuitVersion: "2.0.0",
		CircuitHash:    "3fa24c7763608b01b4c7e411655ebc75ff7a906c38bd79a4cc3be0f4479cdf23",
		InputHash:      "ebf1f0aa67d10b8472fd7f1af22fc9370ecb813243f928b4f5528ab27457fea7",
		OutputHash:     "0c866369e1ab87b0d0b624c0fdeb490aa05fa2524e9368a023308a1437ec5b5b",
		TraceHash:      "e14d0cb8d4a11cf1db1def3942fa7246b72cb6989463e8d379ade6e90a0405e6",
	}

	// Set proof details
	proofParams := vrl.ProofParams{
		ProofSystem:       "sha256-deterministic",
		ProofBytes:        "0a1b2c3d",
		PublicInputs:      []string{"1a2b3c4d", "2b3c4d5e"},
		VerificationKeyID: "aadfa62983a64cb674b1b9b1c4379d8a01e02948fed731506de4bcf2950012a0",
	}

	// Build the bundle (auto-computes bundle_id, integrity_hash, proof_hash)
	bundle, err := builder.
		SetAIIdentity(aiParams).
		SetComputation(compParams).
		SetProof(proofParams).
		Build()

	if err != nil {
		panic(err)
	}

	fmt.Printf("Created bundle: %s\n", bundle.BundleID)
}
```

### Verifying a Proof Bundle

```go
package main

import (
	"fmt"
	"io/ioutil"
	"github.com/vrl-protocol/spec/sdk/go/vrl"
)

func main() {
	// Load a bundle from JSON
	data, _ := ioutil.ReadFile("bundle.json")
	bundle, _ := vrl.ParseBundle(data)

	// Verify it
	verifier := vrl.NewVerifier()
	result := verifier.Verify(bundle)

	fmt.Printf("Status: %s\n", result.Status)
	fmt.Printf("Valid:  %v\n", result.Valid)

	for _, step := range result.Steps {
		fmt.Printf("  [%s] %s\n", step.Status, step.StepName)
		if step.Error != "" {
			fmt.Printf("      Error: %s\n", step.Error)
		}
	}
}
```

### Serializing and Deserializing

```go
// Serialize a bundle to JSON
jsonData, _ := vrl.SerializeBundle(bundle)
fmt.Println(string(jsonData))

// Deserialize from JSON
recoveredBundle, _ := vrl.ParseBundle(jsonData)
```

## Core Types

### ProofBundle

The top-level structure containing all proof data:

```go
type ProofBundle struct {
	VRLVersion      string              // "1.0"
	BundleID        string              // UUIDv5(VRL_NAMESPACE, integrity_hash)
	IssuedAt        string              // RFC 3339 timestamp
	AIIdentity      AIIdentity          // AI model identity and attestation
	Computation     Computation         // Input/output/trace hashes
	Proof           Proof               // Cryptographic proof
	DataCommitments []DataCommitment    // Optional: dataset bindings
	Legal           *Legal              // Optional: legal metadata
	ProofGraph      *ProofGraph         // Optional: DAG edges
	TrustContext    *TrustContext       // Optional: trust scores
}
```

### AIIdentity

Claims the identity and attestation of an AI model:

```go
type AIIdentity struct {
	AIID                 string // SHA-256 of model/runtime/config
	ModelName            string
	ModelVersion         string // Semver
	ProviderID           string // e.g., "com.openai", "self"
	ExecutionEnvironment string // "deterministic", "tee", "zk-ml", "api-attested", "unattested"
	ProviderSignature    string // Optional: Ed25519 signature
	TEEAttestationReport  string // Optional: Base64 attestation report
	ParentAIID           string // Optional: for lineage tracking
}
```

### Computation

Records the hashed artifacts:

```go
type Computation struct {
	CircuitID      string // e.g., "trade/import-landed-cost@2.0.0"
	CircuitVersion string // Semver
	CircuitHash    string // SHA-256 of circuit descriptor
	InputHash      string // SHA-256 of canonical JSON inputs
	OutputHash     string // SHA-256 of canonical JSON outputs
	TraceHash      string // SHA-256 of canonical JSON trace
	IntegrityHash  string // SHA-256 of (input_hash + output_hash + trace_hash)
}
```

### Proof

Contains the cryptographic proof:

```go
type Proof struct {
	ProofSystem       string   // "plonk-halo2-pasta", "tee-intel-tdx", etc.
	ProofBytes        string   // Hex-encoded proof bytes
	PublicInputs      []string // Hex-encoded field elements
	VerificationKeyID string   // SHA-256 of verification key
	Commitments       []string // Optional: proof commitments
	ProofHash         string   // SHA-256 of (circuit_hash, proof_bytes, public_inputs, proof_system, trace_hash, public_inputs_hash)
}
```

## Proof Systems

Supported proof systems:

- `plonk-halo2-pasta` — PLONK via Halo2 on Pasta curve
- `plonk-halo2-bn254` — PLONK via Halo2 on BN254 curve
- `groth16-bn254` — Groth16 on BN254 curve
- `stark` — STARKs (transparent, post-quantum)
- `zk-ml` — zkML via EZKL or equivalent
- `tee-intel-tdx` — Intel TDX hardware attestation
- `tee-amd-sev-snp` — AMD SEV-SNP hardware attestation
- `tee-aws-nitro` — AWS Nitro Enclave attestation
- `sha256-deterministic` — SHA-256 hash chain (deterministic engines only)
- `api-hash-binding` — HMAC-SHA256 input/output binding

## Hash Functions

### CanonicalJSON

Marshals a value to canonical JSON with sorted keys and no whitespace:

```go
canonical, err := vrl.CanonicalJSON(map[string]interface{}{
	"z": 1,
	"a": "hello",
	"m": []interface{}{3, 1, 2},
})
// Result: {"a":"hello","m":[3,1,2],"z":1}
```

### SHA256Hex

Computes SHA-256 and returns lowercase hex:

```go
hash := vrl.SHA256Hex("input string")
// Returns: "64-character lowercase hex string"
```

### ComputeIntegrityHash

Computes integrity_hash from three components:

```go
integrityHash := vrl.ComputeIntegrityHash(inputHash, outputHash, traceHash)
```

### ComputeAIID

Computes AI-ID per spec §2.2:

```go
aiid, err := vrl.ComputeAIID(vrl.AIIDParams{
	ModelWeightsHash: "...",
	RuntimeHash:      "...",
	ConfigHash:       "...",
	ProviderID:       "io.example",
	ModelName:        "my-model",
	ModelVersion:     "1.0.0",
	SpecVersion:      "vrl/ai-id/1.0",
})
```

### ComputeProofHash

Computes proof_hash per spec §11.5:

```go
proofHash, err := vrl.ComputeProofHash(vrl.ProofHashParams{
	CircuitHash:      "...",
	ProofBytes:       "...",
	PublicInputs:     []string{"..."},
	ProofSystem:      "plonk-halo2-pasta",
	TraceHash:        "...",
	PublicInputsHash: "...",
})
```

## Verification

The `Verifier` performs complete verification per spec §12:

```go
verifier := vrl.NewVerifier()
result := verifier.Verify(bundle)

switch result.Status {
case vrl.StatusValid:
	fmt.Println("Bundle is valid!")
case vrl.StatusIntegrityMismatch:
	fmt.Println("Integrity hash mismatch - bundle is tampered")
case vrl.StatusProofInvalid:
	fmt.Println("Cryptographic proof verification failed")
default:
	fmt.Printf("Verification failed: %s\n", result.Status)
}
```

### Verification Steps

1. **Version Check** — Verify `vrl_version == "1.0"`
2. **Schema Validation** — Check required fields are present
3. **Bundle ID Recomputation** — Verify `UUIDv5(VRL_NAMESPACE, integrity_hash)`
4. **Integrity Hash Recomputation** — Verify `SHA-256(input_hash + output_hash + trace_hash)`
5. **Circuit Resolution** — Verify circuit_hash format and validity
6. **Proof Verification** — Verify proof_bytes and format
7. **AI-ID Verification** — Verify AI-ID and signature (if present)
8. **Data Commitment Verification** — Verify commitment hashes
9. **Timestamp Verification** — Verify TSA token (if present)
10. **Proof Graph Edges** — Verify dependency bundles (if present)

## CLI Tool

### vrl-verify

Verify a bundle from the command line:

```bash
vrl-verify bundle.json
```

Output:

```
VRL Bundle Verification Report
==============================
Bundle ID:     7f3a1b29-8c4e-5d6f-9a0b-1c2d3e4f5a6b
Status:        VALID
Valid:         true

Verification Steps:
  [1] Version Check                           PASS
  [2] Schema Validation                       PASS
  [3] Bundle ID Recomputation                 PASS
  [4] Integrity Hash Recomputation            PASS
  [5] Circuit Resolution                      PASS (skipped)
  [6] Proof Verification                      PASS
  [7] AI-ID Verification                      PASS
  [8] Data Commitments                        PASS
  [9] Timestamp Verification                  SKIPPED
  [10] Proof Graph Edges                      SKIPPED

Bundle Information:
  VRL Version:              1.0
  Issued At:                2026-04-04T12:00:00.000Z
  AI-ID:                    a3f2c1d4e5b6a7f8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a
  Model:                    vrl-deterministic-engine 1.0.0
  Circuit:                  trade/import-landed-cost@2.0.0
  Proof System:             plonk-halo2-pasta
  Integrity Hash:           7b58cd2c0b85716175e90136d025d8d282abb1b56cb98ffaa33d4cbde3db70a1
  Proof Hash:               c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2

Result: PASS
```

Exit codes:
- `0` — Bundle is valid
- `1` — Bundle is invalid
- `2` — Usage error

## Testing

Run the test suite:

```bash
go test ./...
```

Tests cover:
- Bundle construction with the builder
- Serialize/deserialize round-tripping
- Verification of valid bundles
- Detection of tampered bundles
- Canonical JSON serialization
- SHA-256 hash computation
- Integrity hash computation
- AI-ID computation
- Proof hash computation
- Data commitment verification

## Specification

This SDK implements the **VRL Proof Bundle Specification v1.0**. For full details, see:

- **Canonical Serialization** — §10
- **Hash Computation** — §11
- **Verification Procedure** — §12
- **AI Identity Standard** — §2
- **Proof Systems** — §4

## Limitations

The current implementation:

- Does **not** verify actual ZK proofs (plonk, groth16, stark, etc.) — requires external ZK verifier libraries
- Does **not** verify TEE attestation reports — requires hardware vendor libraries
- Does **not** verify RFC 3161 timestamp tokens — would require external TSA client
- Does **not** access the circuit registry — requires network access to registry service

For production use with cryptographic proof verification, integrate the appropriate ZK verifier library for your proof system.

## License

CC BY 4.0 — Same license as the VRL Specification

## Contributing

Contributions are welcome. Please ensure:

- All tests pass: `go test ./...`
- Code is formatted: `go fmt ./...`
- No external dependencies beyond stdlib
- Changes maintain compatibility with VRL v1.0 spec
