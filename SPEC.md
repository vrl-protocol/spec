# VRL Proof Bundle Specification v1.0

**Status:** Draft
**Version:** 1.0.0
**Published:** 2026-04-04
**Authors:** Verifiable Reality Layer Contributors
**Repository:** https://github.com/vrl-protocol/spec
**License:** CC BY 4.0

---

## Abstract

This document defines the **VRL Proof Bundle** — a portable, self-contained artifact that cryptographically attests to the identity, inputs, outputs, and execution correctness of any AI system or deterministic computation. A VRL Proof Bundle carries enough information for any third party to independently verify its authenticity without trusting the issuing party or any centralised service.

The VRL Proof Bundle is designed to become the universal envelope for verifiable AI output — the equivalent of a TLS certificate for computational truth. It is proof-system-agnostic, jurisdiction-aware, composable into causal graphs, and legally structured for admissibility in regulated contexts.

---

## Status of This Document

This document is a **Draft Specification**. It is open for public review and contribution at `https://github.com/vrl-protocol/spec`. The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** in this document are to be interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

---

## Table of Contents

1. [Terminology](#1-terminology)
2. [AI Identity Standard (AI-ID)](#2-ai-identity-standard-ai-id)
3. [Proof Bundle Structure](#3-proof-bundle-structure)
4. [Proof Systems](#4-proof-systems)
5. [Circuit Registry](#5-circuit-registry)
6. [Data Commitments](#6-data-commitments)
7. [Proof Graph](#7-proof-graph)
8. [Legal Layer](#8-legal-layer)
9. [Trust Context](#9-trust-context)
10. [Canonical Serialisation](#10-canonical-serialisation)
11. [Hash Computation](#11-hash-computation)
12. [Verification Procedure](#12-verification-procedure)
13. [Mandatory Output Envelope](#13-mandatory-output-envelope)
14. [Security Considerations](#14-security-considerations)
15. [Versioning](#15-versioning)
16. [Complete Examples](#16-complete-examples)
17. [JSON Schema](#17-json-schema)

---

## 1. Terminology

**AI-ID** — A cryptographic identifier uniquely bound to a specific AI model at a specific version in a specific execution environment. Defined in §2.

**Circuit** — A deterministic, verifiable computation encoded as a set of arithmetic constraints. Circuits are identified by their circuit hash and registered in the VRL Circuit Registry. See §5.

**Circuit Hash** — The SHA-256 digest of the canonical serialisation of a circuit's constraint system. Immutable once a circuit is registered.

**Data Commitment** — A cryptographic binding between a proof bundle and a specific version of an external dataset, signed by the dataset's authoritative provider. See §6.

**Integrity Hash** — The SHA-256 digest of the concatenation of `input_hash + output_hash + trace_hash`. Binds all three artefacts together into a single verifiable fingerprint.

**Proof Bundle** — The complete, portable artefact defined by this specification. Contains an AI identity claim, a computation record, a cryptographic proof, optional legal metadata, data commitments, and graph edges.

**Proof Graph** — The directed acyclic graph formed when proof bundles reference each other as dependencies or upstream causes. See §7.

**Proof System** — The cryptographic mechanism used to generate and verify the proof within a bundle. Defined proof systems are enumerated in §4.

**TEE** — Trusted Execution Environment. A hardware-isolated compute enclave that generates a signed attestation report binding the code hash, input, and output of a computation.

**Trace** — The ordered sequence of intermediate computation steps between input and output. The trace is canonically serialised and hashed as `trace_hash`.

**Verifier** — Any party that independently checks a proof bundle's validity according to the procedure in §12.

**Witness** — The private assignment of values to circuit variables. The witness is never included in the proof bundle; it is consumed by the prover and discarded.

**VRL DSL** — The domain-specific language used to define circuits in human-readable form, compiled to Halo2 constraints by the VRL circuit compiler.

---

## 2. AI Identity Standard (AI-ID)

### 2.1 Purpose

An AI-ID is a stable, verifiable identifier for a specific AI model at a specific version under a specific execution configuration. It allows any party to assert: *"This exact model, in this exact state, produced this output."*

### 2.2 AI-ID Computation

An AI-ID is computed as:

```
AI_ID = SHA-256(
  canonical_json({
    "model_weights_hash":      SHA-256(model_weights_bytes),
    "runtime_hash":            SHA-256(runtime_environment_descriptor),
    "config_hash":             SHA-256(canonical_json(inference_config)),
    "provider_id":             "<provider canonical name>",
    "model_name":              "<model name>",
    "model_version":           "<semver>",
    "spec_version":            "vrl/ai-id/1.0"
  })
)
```

**model_weights_hash** — The SHA-256 digest of the raw model weights file(s) concatenated in deterministic order. For API-hosted models where weights are not publicly accessible, the provider MUST publish a signed attestation of the weights hash.

**runtime_hash** — The SHA-256 digest of a descriptor string encoding the runtime environment: framework name and version, hardware accelerator type, operating system, and container image hash where applicable. Format: `"<framework>/<version>/<accelerator>/<os>/<container_hash_or_none>"`.

**config_hash** — The SHA-256 digest of the canonical serialisation of the inference configuration object (temperature, top_p, max_tokens, system_prompt_hash, and any other parameters that affect model behaviour).

**provider_id** — A canonical string identifying the entity responsible for operating the model. Recommended format: reverse-domain notation, e.g. `"com.openai"`, `"com.anthropic"`, `"org.meta"`, or `"self"` for self-hosted deployments.

### 2.3 AI-ID Invariants

- The same model weights + runtime + config MUST always produce the same AI-ID.
- Any change to weights, runtime, config, or provider_id MUST produce a different AI-ID.
- AI-IDs are self-sovereign — model providers compute and sign their own AI-IDs. The VRL protocol defines the computation; it does not issue IDs.

### 2.4 Provider Signature

The provider SHOULD sign the AI-ID with their private key:

```json
{
  "ai_id": "<hex>",
  "provider_id": "com.openai",
  "model_name": "gpt-4-turbo",
  "model_version": "2024-04-09",
  "signed_at": "2024-04-09T00:00:00Z",
  "provider_signature": "<base64-encoded Ed25519 signature over ai_id>"
}
```

When a provider signature is present, verifiers MUST check it against the provider's published public key. When absent, the `execution_environment` field MUST be set to `"unattested"` and verifiers SHOULD treat the AI-ID claim as advisory only.

### 2.5 AI-ID Lineage

When a model is updated (e.g. GPT-4 → GPT-4-turbo), the new AI-ID SHOULD declare lineage:

```json
{
  "ai_id": "<new_ai_id>",
  "parent_ai_id": "<prior_ai_id>",
  "lineage_type": "fine-tune | update | distillation | fork"
}
```

This allows trust score history to be partially inherited while distinguishing model versions.

---

## 3. Proof Bundle Structure

### 3.1 Top-Level Fields

A VRL Proof Bundle is a JSON object with the following top-level fields. All fields marked REQUIRED must be present. Fields marked OPTIONAL may be omitted.

```json
{
  "vrl_version":       "<string>  REQUIRED",
  "bundle_id":         "<string>  REQUIRED",
  "issued_at":         "<string>  REQUIRED",
  "ai_identity":       "<object>  REQUIRED",
  "computation":       "<object>  REQUIRED",
  "proof":             "<object>  REQUIRED",
  "data_commitments":  "<array>   OPTIONAL",
  "legal":             "<object>  OPTIONAL",
  "proof_graph":       "<object>  OPTIONAL",
  "trust_context":     "<object>  OPTIONAL"
}
```

### 3.2 vrl_version

```
"vrl_version": "1.0"
```

The version of the VRL Proof Bundle specification this bundle conforms to. MUST be `"1.0"` for bundles conforming to this document.

### 3.3 bundle_id

```
"bundle_id": "<UUIDv5>"
```

A deterministic identifier for this bundle, computed as:

```
bundle_id = UUIDv5(VRL_NAMESPACE, integrity_hash)
```

where `VRL_NAMESPACE = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"` and `integrity_hash` is defined in §3.5.2. This ensures the bundle_id is stable and deterministic for identical computations.

### 3.4 issued_at

```
"issued_at": "2026-04-04T12:00:00.000Z"
```

The UTC timestamp of proof generation in RFC 3339 format with millisecond precision. MUST be UTC (offset `Z`). This is the wall-clock time claimed by the prover; authoritative timestamps are in the `legal` block (§8).

### 3.5 computation

The `computation` object records the hashed artefacts of the computation.

```json
{
  "computation": {
    "circuit_id":       "<string>  REQUIRED",
    "circuit_version":  "<string>  REQUIRED",
    "circuit_hash":     "<string>  REQUIRED",
    "input_hash":       "<string>  REQUIRED",
    "output_hash":      "<string>  REQUIRED",
    "trace_hash":       "<string>  REQUIRED",
    "integrity_hash":   "<string>  REQUIRED"
  }
}
```

**circuit_id** — The human-readable registry identifier of the circuit used. Format: `"<domain>/<name>@<version>"`, e.g. `"trade/import-landed-cost@2.0.0"`.

**circuit_version** — The semver version of the circuit, matching the registry entry.

**circuit_hash** — The SHA-256 digest of the circuit's canonical constraint system. Immutable. Verifiers MUST recompute this from the registered circuit and check it matches.

**input_hash** — SHA-256 of the canonical JSON serialisation of all public and committed inputs. See §10 for canonical serialisation rules.

**output_hash** — SHA-256 of the canonical JSON serialisation of all public outputs.

**trace_hash** — SHA-256 of the canonical JSON serialisation of the ordered trace steps array.

**integrity_hash** — SHA-256 of the concatenation `input_hash + output_hash + trace_hash` (hex strings, no separator). This is the single fingerprint of the entire computation.

### 3.6 ai_identity

```json
{
  "ai_identity": {
    "ai_id":                    "<string>  REQUIRED",
    "model_name":               "<string>  REQUIRED",
    "model_version":            "<string>  REQUIRED",
    "provider_id":              "<string>  REQUIRED",
    "execution_environment":    "<string>  REQUIRED",
    "provider_signature":       "<string>  OPTIONAL",
    "tee_attestation_report":   "<string>  OPTIONAL",
    "parent_ai_id":             "<string>  OPTIONAL"
  }
}
```

**execution_environment** — MUST be one of:
- `"deterministic"` — pure deterministic computation; no ML inference
- `"tee"` — execution inside a hardware TEE with attestation report present
- `"zk-ml"` — ZK proof of ML inference (zkML mode); proof_system must be `"zk-ml"`
- `"api-attested"` — API-hosted model; hash binding only, no hardware attestation
- `"unattested"` — no attestation available; bundle is for audit trail purposes only

**tee_attestation_report** — Base64-encoded hardware attestation report. REQUIRED when `execution_environment = "tee"`. MUST be a valid Intel TDX Quote, AMD SEV-SNP attestation, or AWS Nitro Enclave attestation document.

### 3.7 proof

```json
{
  "proof": {
    "proof_system":         "<string>  REQUIRED",
    "proof_bytes":          "<string>  REQUIRED",
    "public_inputs":        "<array>   REQUIRED",
    "verification_key_id":  "<string>  REQUIRED",
    "commitments":          "<array>   OPTIONAL",
    "proof_hash":           "<string>  REQUIRED"
  }
}
```

**proof_system** — MUST be one of the registered proof systems defined in §4.

**proof_bytes** — Hex-encoded bytes of the cryptographic proof. For TEE attestation mode, this field contains the hex-encoded attestation report. For hash-binding mode, this field is the hex-encoded HMAC-SHA256 of `input_hash + output_hash`.

**public_inputs** — Ordered array of hex-encoded field elements corresponding to the circuit's instance column. MUST match the instance values used during proof generation.

**verification_key_id** — The SHA-256 digest of the verification key used. Verifiers MUST resolve this to the actual verification key via the circuit registry.

**proof_hash** — SHA-256 of `canonical_json({ proof_bytes, public_inputs, proof_system, circuit_hash, trace_hash, public_inputs_hash })`. Binds the proof artefact to the computation context.

---

## 4. Proof Systems

### 4.1 Registered Proof Systems

| proof_system             | Description                                      | Proof Strength |
|--------------------------|--------------------------------------------------|----------------|
| `plonk-halo2-pasta`      | PLONK via Halo2 on Pasta curve (EqAffine/Fp)     | Cryptographic  |
| `plonk-halo2-bn254`      | PLONK via Halo2 on BN254 curve                   | Cryptographic  |
| `groth16-bn254`          | Groth16 on BN254 curve                           | Cryptographic  |
| `stark`                  | STARKs (transparent, post-quantum)               | Cryptographic  |
| `zk-ml`                  | zkML via EZKL or equivalent                      | Cryptographic  |
| `tee-intel-tdx`          | Intel TDX hardware attestation                   | Hardware       |
| `tee-amd-sev-snp`        | AMD SEV-SNP hardware attestation                 | Hardware       |
| `tee-aws-nitro`          | AWS Nitro Enclave attestation                    | Hardware       |
| `sha256-deterministic`   | SHA-256 hash chain (deterministic engines only)  | Hash-chain     |
| `api-hash-binding`       | HMAC-SHA256 input/output binding (weakest)       | Hash-binding   |

Implementations MUST support `plonk-halo2-pasta` and `sha256-deterministic`. Support for other proof systems is OPTIONAL.

### 4.2 Proof System Upgrade Path

Circuits and proof bundles declare their proof system explicitly. This allows safe migration between proof systems: a circuit may be re-registered under a stronger proof system while maintaining the same circuit_id. Both proof bundles remain independently verifiable against their declared proof system.

---

## 5. Circuit Registry

### 5.1 Circuit Identity

Every circuit is identified by two components:

```
circuit_id      = "<domain>/<name>@<version>"
circuit_hash    = SHA-256(canonical_json(circuit_descriptor))
```

The `circuit_hash` is the immutable cryptographic identity. The `circuit_id` is the human-readable name. Once a circuit is published, its `circuit_hash` is permanently fixed. A version bump always produces a new `circuit_hash`.

### 5.2 Circuit Descriptor

The canonical circuit descriptor is the artefact that determines `circuit_hash`:

```json
{
  "circuit_id":         "trade/import-landed-cost@2.0.0",
  "spec_version":       "vrl/circuit/1.0",
  "constraint_count":   8,
  "input_schema": {
    "private": ["customs_value", "freight", "insurance", "quantity"],
    "public":  ["hs_code", "country_of_origin", "shipping_mode"]
  },
  "output_schema": {
    "public": ["landed_cost", "duty_amount", "mpf_amount", "hmf_amount"]
  },
  "instance_layout": [
    "landed_cost_fp",
    "trace_hash_commitment",
    "circuit_hash_commitment",
    "public_inputs_hash_commitment"
  ],
  "dataset_dependencies": [
    {
      "dataset_id":   "cbp/hts-tariff-rules",
      "min_version":  "2026.1.0"
    }
  ],
  "proof_systems":   ["plonk-halo2-pasta"],
  "vrl_source_hash": "<SHA-256 of VRL DSL source>"
}
```

### 5.3 Certification Tiers

| Tier     | Requirements                                                    |
|----------|-----------------------------------------------------------------|
| `beta`   | Community submitted. Passes automated constraint checks.        |
| `silver` | Automated verification + peer security review. Recommended for non-critical use. |
| `gold`   | Full third-party cryptographic audit + regulatory pre-approval. Required for regulated industries. |

Bundles MUST declare the certification tier of their circuit in the `trust_context` field. Verifiers in regulated contexts SHOULD reject bundles with circuits below `gold` tier.

### 5.4 Circuit Immutability

Once a circuit version is published to the registry with a given `circuit_hash`, it is immutable. The circuit constraints, input/output schema, and dataset dependencies are permanently fixed for that version. Any change requires a new version number and a new `circuit_hash`.

---

## 6. Data Commitments

### 6.1 Purpose

A data commitment binds a proof bundle to a specific, signed version of an external dataset. It answers the question: *"What data did this computation use, and who certified it?"*

### 6.2 Data Commitment Object

```json
{
  "data_commitments": [
    {
      "dataset_id":           "<string>  REQUIRED",
      "dataset_version":      "<string>  REQUIRED",
      "dataset_hash":         "<string>  REQUIRED",
      "provider_id":          "<string>  REQUIRED",
      "provider_signature":   "<string>  RECOMMENDED",
      "committed_at":         "<string>  REQUIRED",
      "commitment_hash":      "<string>  REQUIRED"
    }
  ]
}
```

**dataset_id** — Registry identifier for the dataset. Format: `"<authority>/<name>"`, e.g. `"cbp/hts-tariff-rules"`, `"fda/drug-interaction-database"`, `"ofac/sdn-list"`.

**dataset_hash** — SHA-256 of the canonical dataset content. The circuit uses this hash as a public input to bind the computation to this specific dataset version.

**provider_id** — Canonical identifier of the dataset authority. For government datasets, use the agency identifier, e.g. `"gov.us.cbp"`, `"gov.us.fda"`, `"gov.us.treasury.ofac"`.

**provider_signature** — Base64-encoded Ed25519 signature by the dataset provider over `canonical_json({ dataset_id, dataset_version, dataset_hash, committed_at })`. When present, verifiers MUST validate against the provider's published public key.

**commitment_hash** — SHA-256 of `canonical_json(this_data_commitment_object_without_commitment_hash)`. Used to include the commitment in the integrity chain.

---

## 7. Proof Graph

### 7.1 Purpose

The proof graph is the directed acyclic graph formed by proof bundles that reference each other. It enables complete forensic reconstruction of any AI decision's causal chain — tracing backwards through every model, dataset, and prior computation that contributed to a final output.

### 7.2 Proof Graph Object

```json
{
  "proof_graph": {
    "depends_on":             ["<bundle_id>"],
    "produced_by":            "<bundle_id>",
    "causal_depth":           3,
    "graph_root_hash":        "<string>",
    "privacy_tier":           "public | permissioned | private"
  }
}
```

**depends_on** — Array of `bundle_id` values that this bundle's computation depends on. E.g. a medical decision bundle would list the diagnostic AI bundle_id it used as input.

**produced_by** — The `bundle_id` of the AI inference bundle that generated the output this bundle is verifying. Creates the link between "model ran" and "calculation was correct."

**causal_depth** — The depth of this bundle in its causal chain. A root bundle (no `depends_on`) has depth 0. Each dependent layer increments by 1.

**graph_root_hash** — SHA-256 of the ordered concatenation of all `bundle_id` values in this bundle's complete causal chain, depth-first. Provides a single fingerprint for the entire causal graph up to this point.

**privacy_tier** — Controls graph edge visibility:
- `"public"` — edges and node metadata are publicly visible
- `"permissioned"` — edges are visible only to authorised parties; content is ZK-attested
- `"private"` — node provably exists in the graph (its `bundle_id` is anchored) but all content is zero-knowledge

### 7.3 Graph Integrity

The proof graph is append-only. Once a `bundle_id` is published, its `depends_on` edges are immutable. This guarantees that the causal history of any decision cannot be retroactively altered.

---

## 8. Legal Layer

### 8.1 Legal Object

```json
{
  "legal": {
    "jurisdictions":          ["<string>"],
    "admissibility_standard": "<string>",
    "compliance_flags":       ["<string>"],
    "timestamp_authority": {
      "tsa_token":            "<string>",
      "tsa_provider":         "<string>",
      "tsa_hash_algorithm":   "<string>"
    },
    "immutable_anchor": {
      "chain":                "<string>",
      "tx_hash":              "<string>",
      "block_number":         12345678,
      "anchored_at":          "<string>"
    }
  }
}
```

### 8.2 Jurisdictions

Array of ISO 3166-1 alpha-2 country codes or regional identifiers declaring the legal contexts in which this bundle is intended to be admissible. Examples: `["US"]`, `["EU", "GB"]`, `["US", "EU", "AU"]`.

### 8.3 Admissibility Standard

String identifying the evidentiary standard being claimed. MUST be `"VRL_v1"` for bundles conforming to this specification. Future versions will introduce `"VRL_v2"` etc.

### 8.4 Compliance Flags

Array of compliance framework identifiers this bundle is designed to satisfy. Defined values:

| Flag             | Framework                                         |
|------------------|---------------------------------------------------|
| `EU_AI_ACT`      | EU Artificial Intelligence Act (Article 13, 17)   |
| `HIPAA`          | US Health Insurance Portability and Accountability Act |
| `SOX`            | US Sarbanes-Oxley Act (Section 302, 404)          |
| `GDPR`           | EU General Data Protection Regulation             |
| `FCRA`           | US Fair Credit Reporting Act                      |
| `ECOA`           | US Equal Credit Opportunity Act                   |
| `FDA_SAMD`       | FDA Software as Medical Device guidance           |
| `CBP_ACE`        | US Customs and Border Protection ACE requirements |
| `BASEL_III`      | Basel III / CRD IV risk framework                 |

### 8.5 Timestamp Authority

When present, the `timestamp_authority` block provides an RFC 3161-compliant timestamp token that proves the bundle existed at a specific time, signed by a trusted timestamp authority.

**tsa_token** — Base64-encoded RFC 3161 TimeStampToken over the `integrity_hash`.
**tsa_provider** — Human-readable name of the TSA, e.g. `"DigiCert Timestamp CA"`.
**tsa_hash_algorithm** — Hash algorithm used by the TSA, e.g. `"SHA-256"`.

### 8.6 Immutable Anchor

When present, the `immutable_anchor` block records a transaction on a public blockchain that commits to the bundle's `integrity_hash`. This provides a globally verifiable, censorship-resistant timestamp.

**chain** — Chain identifier: `"ethereum"`, `"polygon"`, `"starknet"`, or `"bitcoin"`.
**tx_hash** — The transaction hash on the specified chain.
**block_number** — Block number of the anchoring transaction.
**anchored_at** — UTC timestamp of the block, RFC 3339 format.

Verifiers MAY independently confirm the anchor by querying the specified chain and checking that `integrity_hash` is committed in the transaction data.

---

## 9. Trust Context

```json
{
  "trust_context": {
    "prover_id":                  "<string>",
    "prover_version":             "<string>",
    "trust_score_at_issuance":    0.97,
    "circuit_certification_tier": "gold",
    "anomaly_flags":              []
  }
}
```

**prover_id** — Identifier of the prover node that generated this bundle. Self-assigned; included for audit purposes.

**trust_score_at_issuance** — The trust score of the `ai_id` at the time this bundle was issued. Floating-point value in [0.0, 1.0]. Derived from the VRL Trust Score Engine's computation over historical proof records for this AI-ID.

**circuit_certification_tier** — The certification tier of the circuit at the time of proof generation: `"beta"`, `"silver"`, or `"gold"`.

**anomaly_flags** — Array of anomaly identifiers detected during proof generation. Empty array indicates no anomalies. Defined anomaly codes will be published in a separate registry.

---

## 10. Canonical Serialisation

All hash computations in this specification use **canonical JSON serialisation**. Implementations MUST follow these rules exactly:

1. **Key ordering** — Object keys MUST be sorted lexicographically (Unicode code point order) at all levels of nesting, recursively.
2. **No whitespace** — The serialised output MUST contain no whitespace (no spaces, tabs, or newlines) outside of string values.
3. **String encoding** — Strings MUST be encoded as UTF-8. Unicode escape sequences MUST use lowercase hex (`\u00e9`, not `\u00E9`).
4. **Number encoding** — All numeric values used in hash computation MUST be serialised as strings in the proof bundle to avoid floating-point precision loss. Decimal values MUST use fixed-point notation (e.g. `"450.00"`, not `"4.5e2"`).
5. **Boolean and null** — `true`, `false`, and `null` serialised as-is with no quotes.
6. **Array ordering** — Arrays are ordered. Element order is preserved exactly.
7. **No trailing commas** — Standard JSON; no trailing commas.

Example: the object `{ "z": 1, "a": "hello", "m": [3, 1, 2] }` canonicalises to:
`{"a":"hello","m":[3,1,2],"z":1}`

---

## 11. Hash Computation

All hash computations in this specification use **SHA-256** producing a **lowercase hex-encoded** 64-character string.

### 11.1 input_hash

```
input_hash = SHA-256(canonical_json(inputs_object))
```

where `inputs_object` is the complete set of computation inputs (both public and private fields that are committed to), with all numeric values represented as strings per §10.

### 11.2 output_hash

```
output_hash = SHA-256(canonical_json(outputs_object))
```

### 11.3 trace_hash

```
trace_hash = SHA-256(canonical_json(trace_steps_array))
```

where `trace_steps_array` is the ordered array of trace step objects, each containing `step`, `rule_ref`, `inputs`, and `outputs` fields with string-valued numerics.

### 11.4 integrity_hash

```
integrity_hash = SHA-256(input_hash + output_hash + trace_hash)
```

where `+` denotes string concatenation of the three lowercase hex strings. No separator. Total input to SHA-256 is 192 characters.

### 11.5 proof_hash

```
proof_hash = SHA-256(canonical_json({
  "circuit_hash":        "<hex>",
  "proof_bytes":         "<hex>",
  "public_inputs":       ["<hex>", ...],
  "proof_system":        "<string>",
  "trace_hash":          "<hex>",
  "public_inputs_hash":  "<hex>"
}))
```

### 11.6 AI-ID

Defined in §2.2.

### 11.7 bundle_id

```
bundle_id = UUIDv5(VRL_NAMESPACE_UUID, integrity_hash)
VRL_NAMESPACE_UUID = "d9ec1f3e-2d27-45d4-af5f-d8d5efcb7c1e"
```

---

## 12. Verification Procedure

A **verifier** is any party checking a proof bundle's validity. Verification MUST be executable offline using only the bundle itself and the publicly available circuit registry.

### 12.1 Steps

**Step 1 — Version Check**
Check `vrl_version == "1.0"`. If the version is not supported, halt with `UNSUPPORTED_VERSION`.

**Step 2 — Schema Validation**
Validate the bundle against the JSON Schema in §17. Any schema violation produces `SCHEMA_INVALID`.

**Step 3 — bundle_id Recomputation**
Recompute `UUIDv5(VRL_NAMESPACE_UUID, bundle.computation.integrity_hash)`. Check it matches `bundle.bundle_id`. Mismatch produces `BUNDLE_ID_MISMATCH`.

**Step 4 — Integrity Hash Recomputation**
Recompute `SHA-256(input_hash + output_hash + trace_hash)`. Check it matches `bundle.computation.integrity_hash`. Mismatch produces `INTEGRITY_MISMATCH`.

**Step 5 — Circuit Resolution**
Resolve `bundle.computation.circuit_id` and `bundle.computation.circuit_version` from the circuit registry. Verify that `bundle.computation.circuit_hash` matches the registered circuit's hash. Mismatch produces `CIRCUIT_HASH_MISMATCH`.

**Step 6 — Proof Verification**
Based on `bundle.proof.proof_system`:
- `plonk-halo2-*` or `groth16-*` — run the ZK verifier with `proof_bytes`, `public_inputs`, and the resolved verification key. Failure produces `PROOF_INVALID`.
- `tee-*` — verify the `tee_attestation_report` against the hardware vendor's root certificate. Failure produces `TEE_ATTESTATION_INVALID`.
- `sha256-deterministic` — recompute the computation from the original inputs and verify all four hashes match. Mismatch produces `RECOMPUTATION_MISMATCH`.
- `api-hash-binding` — verify the HMAC-SHA256 over `input_hash + output_hash`. Failure produces `HASH_BINDING_INVALID`.

**Step 7 — AI-ID Verification (if provider_signature present)**
Recompute the `ai_id` per §2.2. Check it matches `bundle.ai_identity.ai_id`. Verify the `provider_signature` against the provider's published public key. Failure produces `AI_ID_INVALID`.

**Step 8 — Data Commitment Verification (if present)**
For each data commitment: recompute `commitment_hash`, verify it matches the stored value. If `provider_signature` is present, verify it. Mismatch produces `DATA_COMMITMENT_INVALID`.

**Step 9 — Timestamp Verification (if legal.timestamp_authority present)**
Validate the RFC 3161 TSA token against the TSA's certificate chain. Check the token covers `integrity_hash`. Failure produces `TIMESTAMP_INVALID`.

**Step 10 — Proof Graph Edges (if proof_graph present)**
For each `bundle_id` in `depends_on`, the verifier MAY fetch and recursively verify the referenced bundle. Graph integrity failure produces `GRAPH_EDGE_INVALID`.

### 12.2 Verification Result

A verification result MUST be one of:

| Result                      | Meaning |
|-----------------------------|---------|
| `VALID`                     | All required checks passed |
| `VALID_PARTIAL`             | Core proof valid; optional checks (TSA, graph) not performed |
| `SCHEMA_INVALID`            | Bundle does not conform to §17 |
| `BUNDLE_ID_MISMATCH`        | bundle_id does not match recomputed value |
| `INTEGRITY_MISMATCH`        | integrity_hash does not match recomputed value |
| `CIRCUIT_HASH_MISMATCH`     | Circuit hash does not match registry |
| `PROOF_INVALID`             | ZK proof verification failed |
| `TEE_ATTESTATION_INVALID`   | TEE report invalid or untrusted |
| `RECOMPUTATION_MISMATCH`    | Deterministic recomputation produced different result |
| `HASH_BINDING_INVALID`      | HMAC-SHA256 hash binding failed |
| `AI_ID_INVALID`             | AI-ID recomputation or signature check failed |
| `DATA_COMMITMENT_INVALID`   | Data commitment hash or signature failed |
| `TIMESTAMP_INVALID`         | RFC 3161 TSA token invalid |
| `GRAPH_EDGE_INVALID`        | A referenced dependency bundle failed verification |
| `UNSUPPORTED_VERSION`       | vrl_version is not supported by this verifier |

---

## 13. Mandatory Output Envelope

Systems that wish to declare VRL compliance SHOULD wrap AI outputs in the following envelope:

```json
{
  "output": "<the raw AI output — string, object, or array>",
  "vrl": {
    "bundle_id":        "<string>",
    "integrity_hash":   "<string>",
    "proof_system":     "<string>",
    "ai_id":            "<string>",
    "trust_score":      0.97,
    "issued_at":        "<RFC3339>",
    "verify_url":       "https://verify.vrl.io/bundle/<bundle_id>"
  }
}
```

The `vrl` field provides a lightweight summary. The full bundle is retrievable via `verify_url` or by passing the `bundle_id` to any VRL-compatible verifier.

The `verify_url` field MUST point to a publicly accessible endpoint that returns the full proof bundle for the given `bundle_id`. The canonical public verifier is `https://verify.vrl.io`. Organisations MAY operate private verifiers.

---

## 14. Security Considerations

### 14.1 Canonicalisation Attacks

Implementations MUST use the canonical serialisation rules in §10 precisely. A non-canonical serialisation of the same logical object may produce a different hash, enabling an attacker to create a bundle that appears valid under one serialisation but fails under another. Reference implementations MUST include canonicalisation test vectors.

### 14.2 Proof System Soundness

The security of ZK proofs (`plonk-halo2-*`, `groth16-*`) depends on the cryptographic hardness assumptions of the underlying curve. Implementations MUST use well-audited proving system libraries. The VRL project maintains a list of approved implementations.

TEE attestation (`tee-*`) provides hardware-rooted trust but is subject to firmware vulnerabilities. Verifiers SHOULD check that the TEE firmware version is above the minimum patched version for known vulnerabilities (e.g. CVE-listed Intel TDX advisories).

`api-hash-binding` provides no proof of correct computation — only that a specific input produced a specific output. This mode is explicitly for audit trail use cases only and MUST NOT be treated as equivalent to ZK or TEE proof modes.

### 14.3 AI-ID Collision Resistance

AI-IDs are 256-bit SHA-256 digests. Collision resistance is equivalent to SHA-256 preimage resistance (128-bit security level). Providers MUST NOT allow two different model configurations to produce the same AI-ID.

### 14.4 Trust Score Gaming

Trust scores derived from proof history are subject to Sybil attacks — an entity generating large volumes of valid-but-trivial proofs to inflate their score. Implementations of the trust score engine MUST apply proof diversity weighting (penalising repeated identical inputs) and SHOULD require stake to accumulate trust score above a baseline threshold.

### 14.5 Replay Protection

Each `bundle_id` is globally unique (UUIDv5 derived from `integrity_hash`). Two computations with identical inputs to the same circuit will produce the same `bundle_id`. Persistence layers MUST enforce uniqueness on `bundle_id` and return a `409 Conflict` on duplicate submission, rather than silently accepting a replay.

### 14.6 Key Rotation

Verification keys and provider signing keys will require rotation over time. The circuit registry MUST maintain a key rotation log. Proof bundles reference keys by their hash (`verification_key_id`); verifiers MUST resolve the key at the time of proof generation, not the current key, to correctly verify historical bundles.

### 14.7 Offline Verification

Verifiers MUST be able to verify the core proof (Steps 1–6 of §12) without any network access, using only the bundle and a locally cached circuit registry snapshot. This ensures verifiability in air-gapped, regulated, and disconnected environments. Optional steps (TSA, graph edges) may require network access.

---

## 15. Versioning

### 15.1 Specification Versioning

The VRL Proof Bundle specification follows semantic versioning:
- **Major version** changes introduce breaking schema changes that require new verifiers
- **Minor version** changes add optional fields or new proof systems; existing verifiers remain compatible
- **Patch version** changes correct errors or ambiguities in the specification without changing behaviour

### 15.2 Backwards Compatibility

Verifiers implementing v1.x MUST be able to verify all bundles with `vrl_version` matching `"1.*"`. Verifiers MUST NOT reject bundles with unknown optional fields (forward compatibility).

### 15.3 Circuit Versioning

Circuit versions are independent of the specification version. A circuit may be at version `3.1.0` while the specification remains at `1.0`. Circuit version bumps always produce new `circuit_hash` values.

---

## 16. Complete Examples

### 16.1 Deterministic Computation Bundle (Import Landed Cost)

```json
{
  "vrl_version": "1.0",
  "bundle_id": "7f3a1b29-8c4e-5d6f-9a0b-1c2d3e4f5a6b",
  "issued_at": "2026-04-04T12:00:00.000Z",

  "ai_identity": {
    "ai_id": "a3f2c1d4e5b6a7f8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2",
    "model_name": "vrl-deterministic-engine",
    "model_version": "1.0.0",
    "provider_id": "io.vrl",
    "execution_environment": "deterministic"
  },

  "computation": {
    "circuit_id": "trade/import-landed-cost@2.0.0",
    "circuit_version": "2.0.0",
    "circuit_hash": "3fa24c7763608b01b4c7e411655ebc75ff7a906c38bd79a4cc3be0f4479cdf23",
    "input_hash": "ebf1f0aa67d10b8472fd7f1af22fc9370ecb813243f928b4f5528ab27457fea7",
    "output_hash": "0c866369e1ab87b0d0b624c0fdeb490aa05fa2524e9368a023308a1437ec5b5b",
    "trace_hash": "e14d0cb8d4a11cf1db1def3942fa7246b72cb6989463e8d379ade6e90a0405e6",
    "integrity_hash": "7b58cd2c0b85716175e90136d025d8d282abb1b56cb98ffaa33d4cbde3db70a1"
  },

  "proof": {
    "proof_system": "plonk-halo2-pasta",
    "proof_bytes": "0a1b2c3d...",
    "public_inputs": [
      "0x1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b",
      "0x2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c"
    ],
    "verification_key_id": "aadfa62983a64cb674b1b9b1c4379d8a01e02948fed731506de4bcf2950012a0",
    "proof_hash": "c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2"
  },

  "data_commitments": [
    {
      "dataset_id": "cbp/hts-tariff-rules",
      "dataset_version": "2026.1.0",
      "dataset_hash": "d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5",
      "provider_id": "gov.us.cbp",
      "committed_at": "2026-04-01T00:00:00.000Z",
      "commitment_hash": "e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6"
    }
  ],

  "legal": {
    "jurisdictions": ["US"],
    "admissibility_standard": "VRL_v1",
    "compliance_flags": ["CBP_ACE"]
  },

  "trust_context": {
    "prover_id": "vrl-prover-primary",
    "prover_version": "1.0.0",
    "trust_score_at_issuance": 1.0,
    "circuit_certification_tier": "gold",
    "anomaly_flags": []
  }
}
```

### 16.2 TEE-Attested LLM Bundle

```json
{
  "vrl_version": "1.0",
  "bundle_id": "9a8b7c6d-5e4f-3a2b-1c0d-e9f8a7b6c5d4",
  "issued_at": "2026-04-04T14:30:00.000Z",

  "ai_identity": {
    "ai_id": "f1e2d3c4b5a6978869504132231415fa16718192021222324252627282930313233",
    "model_name": "llama-3-70b-instruct",
    "model_version": "3.0.0",
    "provider_id": "self",
    "execution_environment": "tee",
    "tee_attestation_report": "<base64-encoded Intel TDX Quote>"
  },

  "computation": {
    "circuit_id": "general/tee-inference-attestation@1.0.0",
    "circuit_version": "1.0.0",
    "circuit_hash": "b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3",
    "input_hash": "c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4",
    "output_hash": "d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5",
    "trace_hash": "e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6",
    "integrity_hash": "f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7"
  },

  "proof": {
    "proof_system": "tee-intel-tdx",
    "proof_bytes": "<hex-encoded TDX attestation report>",
    "public_inputs": [],
    "verification_key_id": "intel-tdx-root-ca-2024",
    "proof_hash": "a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8"
  },

  "legal": {
    "jurisdictions": ["US", "EU"],
    "admissibility_standard": "VRL_v1",
    "compliance_flags": ["EU_AI_ACT", "GDPR"]
  },

  "proof_graph": {
    "depends_on": [],
    "privacy_tier": "public",
    "causal_depth": 0,
    "graph_root_hash": "f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7"
  }
}
```

---

## 17. JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://spec.vrl.io/v1/proof-bundle.schema.json",
  "title": "VRL Proof Bundle v1.0",
  "type": "object",
  "required": ["vrl_version", "bundle_id", "issued_at", "ai_identity", "computation", "proof"],
  "additionalProperties": true,
  "properties": {
    "vrl_version": { "type": "string", "enum": ["1.0"] },
    "bundle_id":   { "type": "string", "format": "uuid" },
    "issued_at":   { "type": "string", "format": "date-time" },
    "ai_identity": {
      "type": "object",
      "required": ["ai_id", "model_name", "model_version", "provider_id", "execution_environment"],
      "properties": {
        "ai_id":                  { "type": "string", "pattern": "^[0-9a-f]{64}$" },
        "model_name":             { "type": "string" },
        "model_version":          { "type": "string" },
        "provider_id":            { "type": "string" },
        "execution_environment":  { "type": "string", "enum": ["deterministic","tee","zk-ml","api-attested","unattested"] },
        "provider_signature":     { "type": "string" },
        "tee_attestation_report": { "type": "string" },
        "parent_ai_id":           { "type": "string", "pattern": "^[0-9a-f]{64}$" }
      }
    },
    "computation": {
      "type": "object",
      "required": ["circuit_id","circuit_version","circuit_hash","input_hash","output_hash","trace_hash","integrity_hash"],
      "properties": {
        "circuit_id":      { "type": "string" },
        "circuit_version": { "type": "string" },
        "circuit_hash":    { "type": "string", "pattern": "^[0-9a-f]{64}$" },
        "input_hash":      { "type": "string", "pattern": "^[0-9a-f]{64}$" },
        "output_hash":     { "type": "string", "pattern": "^[0-9a-f]{64}$" },
        "trace_hash":      { "type": "string", "pattern": "^[0-9a-f]{64}$" },
        "integrity_hash":  { "type": "string", "pattern": "^[0-9a-f]{64}$" }
      }
    },
    "proof": {
      "type": "object",
      "required": ["proof_system","proof_bytes","public_inputs","verification_key_id","proof_hash"],
      "properties": {
        "proof_system":        { "type": "string" },
        "proof_bytes":         { "type": "string" },
        "public_inputs":       { "type": "array", "items": { "type": "string" } },
        "verification_key_id": { "type": "string" },
        "commitments":         { "type": "array", "items": { "type": "string" } },
        "proof_hash":          { "type": "string", "pattern": "^[0-9a-f]{64}$" }
      }
    },
    "data_commitments": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["dataset_id","dataset_version","dataset_hash","provider_id","committed_at","commitment_hash"],
        "properties": {
          "dataset_id":         { "type": "string" },
          "dataset_version":    { "type": "string" },
          "dataset_hash":       { "type": "string", "pattern": "^[0-9a-f]{64}$" },
          "provider_id":        { "type": "string" },
          "provider_signature": { "type": "string" },
          "committed_at":       { "type": "string", "format": "date-time" },
          "commitment_hash":    { "type": "string", "pattern": "^[0-9a-f]{64}$" }
        }
      }
    },
    "legal": {
      "type": "object",
      "properties": {
        "jurisdictions":          { "type": "array", "items": { "type": "string" } },
        "admissibility_standard": { "type": "string" },
        "compliance_flags":       { "type": "array", "items": { "type": "string" } },
        "timestamp_authority": {
          "type": "object",
          "properties": {
            "tsa_token":          { "type": "string" },
            "tsa_provider":       { "type": "string" },
            "tsa_hash_algorithm": { "type": "string" }
          }
        },
        "immutable_anchor": {
          "type": "object",
          "properties": {
            "chain":        { "type": "string" },
            "tx_hash":      { "type": "string" },
            "block_number": { "type": "integer" },
            "anchored_at":  { "type": "string", "format": "date-time" }
          }
        }
      }
    },
    "proof_graph": {
      "type": "object",
      "properties": {
        "depends_on":      { "type": "array", "items": { "type": "string", "format": "uuid" } },
        "produced_by":     { "type": "string", "format": "uuid" },
        "causal_depth":    { "type": "integer", "minimum": 0 },
        "graph_root_hash": { "type": "string", "pattern": "^[0-9a-f]{64}$" },
        "privacy_tier":    { "type": "string", "enum": ["public","permissioned","private"] }
      }
    },
    "trust_context": {
      "type": "object",
      "properties": {
        "prover_id":                  { "type": "string" },
        "prover_version":             { "type": "string" },
        "trust_score_at_issuance":    { "type": "number", "minimum": 0, "maximum": 1 },
        "circuit_certification_tier": { "type": "string", "enum": ["beta","silver","gold"] },
        "anomaly_flags":              { "type": "array", "items": { "type": "string" } }
      }
    }
  }
}
```

---

## Changelog

| Version | Date       | Changes |
|---------|------------|---------|
| 1.0.0   | 2026-04-04 | Initial specification |

---

## Contributing

This specification is open for contribution at `https://github.com/vrl-protocol/spec`. To propose a change, open a GitHub Issue describing the problem and proposed solution. Breaking changes require a major version bump and a migration guide. Non-breaking additions require a minor version bump.

---

*Copyright 2026 Verifiable Reality Layer Contributors. Licensed under CC BY 4.0.*
