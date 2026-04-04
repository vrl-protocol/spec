# VRL — Verifiable Reality Layer

**The open standard for cryptographically verifiable AI outputs.**

Every AI decision made today leaves no receipt. You cannot prove which model ran, on what data, with what logic, producing what result. For healthcare, finance, law, and government — that is not acceptable.

VRL is the infrastructure layer that fixes this. A portable, self-contained proof bundle that any third party can verify offline — no trust in any server required.

---

## What is a VRL Proof Bundle?

A VRL Proof Bundle is a cryptographic artifact that attaches to any AI output and proves:

- **Which AI ran** — a cryptographic AI Identity (AI-ID) bound to specific model weights, runtime, and configuration
- **What it computed** — input hash, output hash, execution trace hash, bound into a single integrity hash
- **That it ran correctly** — a ZK proof (PLONK/Halo2), TEE hardware attestation, or deterministic recomputation proof
- **On what data** — signed dataset commitments linking computation to specific, authoritative data versions
- **When and where** — RFC 3161 timestamp authority + optional on-chain immutable anchor
- **For what jurisdiction** — legal layer with compliance flags for EU AI Act, HIPAA, SOX, CBP, FDA SaMD, and more

```json
{
  "vrl_version": "1.0",
  "bundle_id": "7f3a1b29-8c4e-5d6f-9a0b-1c2d3e4f5a6b",
  "ai_identity": {
    "ai_id": "a3f2c1d4...",
    "model_name": "llama-3-70b-instruct",
    "execution_environment": "tee"
  },
  "computation": {
    "circuit_id": "trade/import-landed-cost@2.0.0",
    "integrity_hash": "7b58cd2c..."
  },
  "proof": {
    "proof_system": "plonk-halo2-pasta",
    "proof_bytes": "0a1b2c3d..."
  },
  "legal": {
    "jurisdictions": ["US", "EU"],
    "compliance_flags": ["EU_AI_ACT", "CBP_ACE"]
  }
}
```

Any party — regulator, auditor, court, enterprise — can verify this bundle offline using the open spec and the public circuit registry. No trust in VRL required.

---

## Repository Layout

```
vrl-protocol/spec
├── SPEC.md                   ← VRL Proof Bundle Specification v1.0
│
├── sdk/
│   └── python/               ← Python SDK (vrl-sdk)
│       ├── vrl/
│       │   ├── bundle.py     ← ProofBundle data model
│       │   ├── builder.py    ← Fluent ProofBundleBuilder API
│       │   ├── verifier.py   ← 10-step Verifier engine
│       │   ├── identity.py   ← AIIdentity + AIIdentityBuilder
│       │   └── hashing.py    ← Hash utilities (spec §10-11)
│       ├── tests/
│       └── setup.py
│
├── verifier/
│   ├── vrl_verify.py         ← Standalone CLI reference verifier
│   └── test_bundles/         ← Example valid + tampered bundles
│
├── registry/
│   ├── registry.json         ← Master circuit registry
│   ├── circuits/             ← Full circuit descriptors
│   ├── schema/               ← JSON Schema for circuit validation
│   └── tools/lookup.py       ← Registry query CLI
│
└── ui/
    └── index.html            ← Web interface
```

---

## The Specification

→ **[Read SPEC.md](./SPEC.md)** — the full VRL Proof Bundle Specification v1.0

| Section | What it covers |
|---------|---------------|
| §2 — AI Identity Standard | How AI-IDs are computed and signed |
| §3 — Proof Bundle Structure | Complete field-by-field schema |
| §4 — Proof Systems | 10 proof modes from ZK to TEE to hash-binding |
| §5 — Circuit Registry | Immutable circuit identity and certification tiers |
| §6 — Data Commitments | Binding computation to signed authoritative datasets |
| §7 — Proof Graph | Causal chains across AI decisions |
| §8 — Legal Layer | Timestamps, on-chain anchors, jurisdiction tags |
| §12 — Verification Procedure | 10-step offline verification with defined error codes |
| §17 — JSON Schema | Machine-readable schema for immediate integration |

---

## Quickstart

### Verify a bundle (no install needed)

```bash
python verifier/vrl_verify.py verifier/test_bundles/valid_trade.json
```

### Install the Python SDK

```bash
cd sdk/python
pip install -e .
```

### Create a proof bundle

```python
from vrl.builder import ProofBundleBuilder

bundle = (
    ProofBundleBuilder()
    .set_ai_identity(
        model_name="my-model",
        model_version="1.0.0",
        provider_id="my-org",
        execution_environment="tee"
    )
    .set_computation(
        circuit_id="trade/import-landed-cost@2.0.0",
        input_hash="abc123...",
        output_hash="def456...",
        trace_hash="ghi789..."
    )
    .set_proof(
        proof_system="sha256-deterministic",
        proof_bytes="",
        public_inputs=[]
    )
    .build()
)

print(bundle.to_json())
```

### Verify a bundle

```python
from vrl.bundle import ProofBundle
from vrl.verifier import Verifier

bundle = ProofBundle.from_json(open("bundle.json").read())
result = Verifier().verify(bundle)

print(result.status)          # "VALID" or "INVALID"
print(result.error_codes)     # [] or ["INTEGRITY_HASH_MISMATCH", ...]
```

### Look up a circuit

```bash
python registry/tools/lookup.py trade/import-landed-cost@2.0.0
python registry/tools/lookup.py --list --domain healthcare
```

---

## Proof Systems Supported

| Mode | Proof Strength | Best For |
|------|---------------|----------|
| `plonk-halo2-pasta` | Cryptographic | Deterministic computations, compliance calculations |
| `tee-intel-tdx` | Hardware | LLM inference in Intel TDX enclaves |
| `tee-amd-sev-snp` | Hardware | Models in AMD SEV-SNP enclaves |
| `zk-ml` | Cryptographic | Small ML models via EZKL |
| `sha256-deterministic` | Hash-chain | Rule engines, verifiable calculations |
| `api-hash-binding` | Hash-binding | API-hosted models, audit trail use cases |

---

## Circuit Registry

The [VRL Circuit Registry](./registry/) is an open, append-only catalog of certified computation circuits. Circuits are the verifiable computation units that VRL proof bundles reference.

**Current circuits:** 8 across 4 domains (trade, healthcare, finance, general)

**Certification tiers:**

| Tier | Description |
|------|-------------|
| `EXPERIMENTAL` | Submitted, not yet reviewed |
| `REVIEWED` | Reviewed by VRL maintainers |
| `CERTIFIED` | Independently audited and formally verified |

→ [Submit a circuit](./registry/SUBMISSION.md)

---

## Why This Exists

The EU AI Act mandates audit trails for high-risk AI systems. The FDA requires documentation for AI-based medical devices. Financial regulators expect explainable, traceable AI decisions. Courts are beginning to accept AI-generated evidence.

None of them have a technical standard to point to.

VRL is that standard.

---

## The Vision

VRL is to AI outputs what TLS is to web connections — not a product you buy, but infrastructure you build on. The goal is that every consequential AI decision in the world carries a VRL proof bundle, and any regulator, enterprise, or citizen can verify it offline.

**The win condition is not being the best technology. It is being the format everything else must comply with.**

---

## Status

| Component | Status |
|-----------|--------|
| Proof Bundle Spec v1.0 | ✅ Published |
| JSON Schema | ✅ Published |
| Python SDK (vrl-sdk) | ✅ v0.1.0 |
| Reference Verifier CLI | ✅ Published |
| Circuit Registry | ✅ 8 circuits live |
| `vrl-sdk` (TypeScript) | 🔜 Planned |
| TEE Attestation Bridge | 🔜 Planned |
| Public Proof Explorer | 🔜 Planned |
| On-chain Anchor Module | 🔜 Planned |

---

## Contributing

This specification and all tooling are open. If you see a gap, an ambiguity, or a missing proof system — open an issue or a pull request.

**To propose a spec change:** open a GitHub Issue describing the problem and the proposed solution. Breaking changes require a major version bump.

**To implement the spec:** build against the JSON Schema in §17 of SPEC.md and validate against the reference verifier test bundles.

**To register a circuit:** follow the [circuit submission guide](./registry/SUBMISSION.md).

---

## License

Specification: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
Reference Implementation: MIT

---

*VRL is being built in public. Follow the progress at [github.com/vrl-protocol](https://github.com/vrl-protocol).*
