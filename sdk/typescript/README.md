# VRL TypeScript/JavaScript SDK

A production-quality TypeScript SDK for building and verifying VRL (Verifiable Reality Layer) Proof Bundles. Implements the complete VRL specification with zero runtime dependencies — only Node.js built-in `crypto`.

## Features

- **Type-Safe**: Full TypeScript strict mode with no `any` types
- **Zero Dependencies**: Uses only Node.js built-in `crypto` module
- **Spec Compliant**: Implements VRL Spec §1-17 completely
- **Fluent API**: Builder pattern for constructing bundles
- **Full Verification**: 10-step verification procedure from VRL Spec §12
- **Canonical Hashing**: SHA-256 with canonical JSON per VRL Spec §10-11
- **Production Ready**: Thoroughly tested, no edge cases

## Installation

```bash
npm install vrl-sdk
```

Requires Node.js 18+.

## Quick Start

### 1. Create a Proof Bundle

```typescript
import {
  ProofBundleBuilder,
  ComputationBuilder,
  ProofBuilder,
  computeIntegrityHash,
  computeProofHash,
} from "vrl-sdk";

// Define AI identity
const aiIdentity = {
  ai_id: "a".repeat(64), // 64-char lowercase hex
  provider_id: "com.openai",
  model_name: "gpt-4",
  model_version: "1.0.0",
  model_weights_hash: "b".repeat(64),
  runtime_hash: "c".repeat(64),
  config_hash: "d".repeat(64),
};

// Build computation with integrity hash
const computation = new ComputationBuilder()
  .setCircuitId("trade/import-landed-cost")
  .setCircuitVersion("2.0.0")
  .setCircuitHash("e".repeat(64))
  .setInputHash("f".repeat(64))
  .setOutputHash("0".repeat(64))
  .setTraceHash("1".repeat(64))
  .computeIntegrityHash() // Auto-computes from input/output/trace
  .build();

// Build proof
const proof = new ProofBuilder()
  .setProofSystem("sha256-deterministic")
  .setProofBytes("2".repeat(128))
  .setPublicInputs(["3".repeat(64)])
  .setVerificationKeyId("4".repeat(64))
  .setProofHash("5".repeat(64))
  .build();

// Build the complete bundle
const bundle = new ProofBundleBuilder()
  .setAIIdentity(aiIdentity)
  .setComputation(computation)
  .setProof(proof)
  .build();

console.log(bundle.bundle_id); // Auto-generated UUID
```

### 2. Verify a Bundle

```typescript
import { Verifier } from "vrl-sdk";

const verifier = new Verifier();
const result = verifier.verify(bundle);

if (result.status === "VALID") {
  console.log("Bundle is valid!");
} else {
  console.log("Verification failed:", result.errorCodes);
  result.steps.forEach((step) => {
    console.log(`- Step ${step.step}: ${step.name} - ${step.passed ? "PASS" : "FAIL"}`);
  });
}
```

### 3. Serialize and Parse

```typescript
import { serializeBundle, parseBundle } from "vrl-sdk";

// Serialize to canonical JSON
const json = serializeBundle(bundle);

// Parse from JSON
const parsed = parseBundle(json);
console.log(parsed.bundle_id);
```

## API Reference

### Builders

#### ProofBundleBuilder

Fluent builder for `ProofBundle`:

```typescript
new ProofBundleBuilder()
  .setAIIdentity(aiIdentity)
  .setComputation(computation)
  .setProof(proof)
  .setLegal(legal)                  // Optional
  .addDataCommitment(commitment)    // Optional
  .setProofGraph(graph)             // Optional
  .setTrustContext(context)         // Optional
  .setIssuedAtNow()                 // Default
  .build()
```

#### ComputationBuilder

Fluent builder for `Computation`:

```typescript
new ComputationBuilder()
  .setCircuitId("circuit/id")
  .setCircuitVersion("1.0.0")
  .setCircuitHash("...")
  .setInputHash("...")
  .setOutputHash("...")
  .setTraceHash("...")
  .computeIntegrityHash()  // Auto-computes
  .build()
```

#### ProofBuilder

Fluent builder for `Proof`:

```typescript
new ProofBuilder()
  .setProofSystem("plonk-halo2-bn254")
  .setProofBytes("hex...")
  .setPublicInputs(["hex...", "hex..."])
  .setVerificationKeyId("...")
  .setProofHash("...")
  .setCommitments(["..."])  // Optional
  .build()
```

### Hash Functions

All hash functions return 64-character lowercase hex strings.

```typescript
import {
  canonicalJson,           // Serialize to canonical JSON
  sha256,                  // SHA-256 hash
  computeIntegrityHash,    // From input/output/trace
  computeProofHash,        // From circuit/proof/inputs
  computeInputHash,        // From inputs object
  computeOutputHash,       // From outputs object
  computeTraceHash,        // From trace steps
  computeCommitmentHash,   // From dataset commitment
} from "vrl-sdk";

const hash = sha256("test");
const integrity = computeIntegrityHash(inputHash, outputHash, traceHash);
```

### Verification

```typescript
import { Verifier } from "vrl-sdk";

const verifier = new Verifier();
const result = verifier.verify(bundle);

// result.status: "VALID" | "VALID_PARTIAL" | error code
// result.errorCodes: string[] of failure codes
// result.steps: VerificationStep[] with details
```

Implements all 10 steps from VRL Spec §12:
1. Version Check
2. Schema Validation
3. bundle_id Recomputation
4. Integrity Hash Recomputation
5. Circuit Resolution
6. Proof Structure Validation
7. AI-ID Verification
8. Data Commitment Verification
9. Timestamp Verification (optional)
10. Proof Graph Edges (optional)

## Types

All types match the VRL specification exactly:

```typescript
import {
  ProofBundle,
  AIIdentity,
  Computation,
  Proof,
  DataCommitment,
  Legal,
  ProofGraph,
  TrustContext,
  ProofSystem,
  CertificationTier,
  VerificationStatus,
} from "vrl-sdk";
```

## Testing

```bash
npm test
```

Runs tests using Node.js built-in `node:test` module. Tests cover:
- Hash functions (canonical JSON, SHA-256)
- Builders (computation, proof, bundle)
- Serialization round-trip
- Verification (valid bundle, tampering detection)
- Error handling

## License

MIT
