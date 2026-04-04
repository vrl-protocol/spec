# VRL Circuit Submission Guide

This document describes how to submit a new circuit to the VRL Circuit Registry, the review process, certification requirements, and the hash computation procedure.

## Submission Process Overview

The submission process consists of:

1. **Development**: Write and test your circuit
2. **Hash Computation**: Compute the immutable `circuit_hash`
3. **Pull Request**: Submit via GitHub PR with proper documentation
4. **Review**: Automated checks + maintainer review
5. **Certification**: Auto-approved for EXPERIMENTAL; manual approval for REVIEWED/CERTIFIED
6. **Publication**: Circuit is merged and registered

The typical timeline:

- **EXPERIMENTAL**: Same-day approval (automated)
- **REVIEWED**: 7-14 days (code review + peer security review)
- **CERTIFIED**: 30-60 days (third-party audit + formal verification)

## Step 1: Develop Your Circuit

### Circuit Requirements

A VRL circuit must:

- Be deterministic and verifiable
- Have clearly defined public and private inputs
- Have clearly defined outputs
- Declare dependencies on any external datasets
- Be encodable in one or more VRL proof systems (Halo2, STARK, etc.)
- Include comprehensive documentation

### Example Circuit Structure

```
circuits/
├── my-circuit/
│   ├── README.md              # Circuit documentation
│   ├── descriptor.json        # Circuit descriptor
│   ├── src/
│   │   ├── lib.rs            # Rust source (example)
│   │   └── circuit.halo2     # VRL DSL source
│   ├── tests/
│   │   └── integration_tests.rs
│   └── docs/
│       └── math.md            # Mathematical spec
```

## Step 2: Write the Circuit Descriptor

Create a JSON file conforming to `schema/circuit.schema.json`. Here's a template:

```json
{
  "circuit_id": "domain/name@1.0.0",
  "spec_version": "vrl/circuit/1.0",
  "circuit_hash": "computed-below",
  "domain": "trade",
  "name": "my-circuit",
  "version": "1.0.0",
  "description": "One-line description",
  "long_description": "Detailed description...",
  "input_schema": {
    "private": [
      {
        "name": "private_input",
        "type": "integer",
        "description": "Description"
      }
    ],
    "public": [
      {
        "name": "public_input",
        "type": "string",
        "description": "Description"
      }
    ]
  },
  "output_schema": {
    "public": [
      {
        "name": "output",
        "type": "integer",
        "description": "Description"
      }
    ]
  },
  "proof_systems": ["plonk-halo2-pasta"],
  "constraint_count": 10,
  "dataset_dependencies": [],
  "certification_tier": "EXPERIMENTAL",
  "published_at": "2026-04-04T00:00:00Z",
  "author": "Your Name or Organization",
  "author_email": "email@example.com",
  "license": "Apache-2.0"
}
```

**Required fields**:

- `circuit_id`: Format `<domain>/<name>@<semver>`
- `spec_version`: Must be `"vrl/circuit/1.0"`
- `circuit_hash`: See "Hash Computation" below
- `domain`: One of: trade, healthcare, finance, general
- `name`, `version`: Part of circuit_id
- `description`: One-line summary (10-200 characters)
- `input_schema`, `output_schema`: Detailed input/output specs
- `proof_systems`: At least one from the approved list
- `constraint_count`: Number of arithmetic constraints
- `certification_tier`: EXPERIMENTAL, REVIEWED, or CERTIFIED
- `published_at`: ISO 8601 timestamp
- `author`, `author_email`, `license`: Attribution

**Optional fields**:

- `long_description`: Detailed explanation
- `instance_layout`: Instance column names
- `dataset_dependencies`: External dataset requirements
- `tags`: For discovery
- `compliance_frameworks`: Regulatory alignment
- `security_notes`: Important security considerations
- `performance_notes`: Benchmark information

## Step 3: Compute the Circuit Hash

The `circuit_hash` is the SHA-256 digest of the **canonical JSON serialization** of the circuit descriptor, excluding the `circuit_hash` field itself.

### Python Implementation

```python
import json
import hashlib

def compute_circuit_hash(descriptor: dict) -> str:
    """Compute circuit_hash according to VRL spec."""
    # Make a copy without circuit_hash
    copy = {k: v for k, v in descriptor.items() if k != 'circuit_hash'}

    # Canonical JSON: sorted keys, no whitespace
    canonical = json.dumps(copy, sort_keys=True, separators=(',', ':'))

    # SHA-256 digest as lowercase hex
    return hashlib.sha256(canonical.encode()).hexdigest()

# Example
descriptor = {
    "circuit_id": "trade/example@1.0.0",
    "spec_version": "vrl/circuit/1.0",
    # ... other fields ...
}

hash_value = compute_circuit_hash(descriptor)
descriptor['circuit_hash'] = hash_value

# Verify (should be consistent)
assert compute_circuit_hash(descriptor) == hash_value
```

### JavaScript Implementation

```javascript
const crypto = require('crypto');

function computeCircuitHash(descriptor) {
  // Make a copy without circuit_hash
  const copy = Object.keys(descriptor)
    .filter(k => k !== 'circuit_hash')
    .sort()
    .reduce((obj, key) => {
      obj[key] = descriptor[key];
      return obj;
    }, {});

  // Canonical JSON: sorted keys, no whitespace
  const canonical = JSON.stringify(copy, null, 0);

  // SHA-256 digest as lowercase hex
  return crypto
    .createHash('sha256')
    .update(canonical)
    .digest('hex');
}
```

### Verification

Once you've computed the hash:

1. Place it in the `circuit_hash` field
2. Recompute to verify it's stable (immutable once set)
3. Include it in the descriptor file

## Step 4: Prepare Files for Submission

### File Structure

```
registry/circuits/
├── domain-name-1.0.0.json          # Descriptor (naming convention)
└── ... (other circuits)
```

**Naming convention**: `<domain>-<name>-<version>.json`

Example: `trade-import-landed-cost-2.0.0.json`

### Validation

Validate your descriptor against the schema:

```bash
# Using ajv (JSON Schema validator)
npm install -g ajv-cli
ajv validate -s schema/circuit.schema.json -d circuits/domain-name-1.0.0.json
```

Or using Python:

```python
import json
import jsonschema

with open('schema/circuit.schema.json') as f:
    schema = json.load(f)

with open('circuits/domain-name-1.0.0.json') as f:
    descriptor = json.load(f)

jsonschema.validate(descriptor, schema)
print("Valid!")
```

## Step 5: Submit via Pull Request

### PR Template

```markdown
## Circuit Submission: domain/name@version

### Details

- **Circuit ID**: domain/name@version
- **Certification Tier**: EXPERIMENTAL / REVIEWED / CERTIFIED
- **Proof System(s)**: plonk-halo2-pasta
- **Constraint Count**: 10

### Description

Brief description of what this circuit does.

### Files

- `circuits/domain-name-1.0.0.json` - Circuit descriptor
- (Optional) `circuits/domain-name-1.0.0/` - Source code and tests

### Testing

- [ ] Circuit descriptor validates against `schema/circuit.schema.json`
- [ ] `circuit_hash` is stable (recomputation yields same hash)
- [ ] All required fields are present
- [ ] Input/output schemas are complete

### For REVIEWED/CERTIFIED

- [ ] Security review checklist completed
- [ ] Test coverage >= 80%
- [ ] Third-party audit report (CERTIFIED only)

### Checklist

- [ ] I confirm this circuit is my original work (or properly attributed)
- [ ] I have read the VRL Specification (SPEC.md §5)
- [ ] I understand the certification tiers and requirements
- [ ] I accept the CC BY 4.0 license for the descriptor
```

### PR Title Format

```
[EXPERIMENTAL | REVIEWED | CERTIFIED] Add circuit: domain/name@version
```

Examples:
- `[EXPERIMENTAL] Add circuit: trade/example@1.0.0`
- `[REVIEWED] Add circuit: healthcare/cds@1.0.0`
- `[CERTIFIED] Add circuit: finance/fraud-detection@1.0.0`

## Review Process

### EXPERIMENTAL Tier

**Automated checks** (must pass):
- JSON schema validation
- Circuit hash stability
- No duplicate circuit_id
- All required fields present

**Timeline**: Approval same-day if checks pass

**What happens**: Auto-merged; circuit immediately available in registry

### REVIEWED Tier

**Additional requirements**:
- Code review by 2 VRL maintainers
- Security review for cryptographic soundness
- Documentation completeness check
- Test coverage >= 80%

**Timeline**: 7-14 days

**Checklist**:
- [ ] Does the circuit descriptor accurately describe the implementation?
- [ ] Are the input/output schemas correct and complete?
- [ ] Are dataset dependencies correctly specified?
- [ ] Is the security context appropriate for the use case?
- [ ] Are there known attacks or edge cases not addressed?
- [ ] Is the constraint count realistic?

**What happens**: After approval, circuit is merged and published

### CERTIFIED Tier

**Additional requirements**:
- Everything in REVIEWED, plus:
- Third-party audit by independent security firm
- Formal verification of constraints (where applicable)
- Regulatory pre-approval (if applicable)
- Proof system cryptanalysis

**Approved auditors**:
- Trail of Bits
- OpenZeppelin
- Least Authority
- Certora
- Other recognized firms (contact maintainers)

**Timeline**: 30-60 days

**What happens**: After audit approval, circuit is published with CERTIFIED badge

## Certification Tiers: Technical Details

| Aspect | EXPERIMENTAL | REVIEWED | CERTIFIED |
|--------|--------------|----------|-----------|
| Approval Time | Same-day | 7-14 days | 30-60 days |
| Review Level | Automated | Manual + Peer | Independent Audit |
| Assurance | Low | Medium | High |
| For Production | No | Yes (non-regulated) | Yes (regulated) |
| Suitable For | R&D, Testing | Business Logic | Legal Evidence |
| Hash Immutability | ✓ | ✓ | ✓ |
| Dataset Verification | ✓ | ✓ | ✓ |
| Proof Verification | ✓ | ✓ | ✓ |
| Cryptographic Audit | No | Maintainers | Third-party |
| Formal Verification | No | No | Yes |

## Hash Immutability

Once a `circuit_hash` is published:

- The hash is permanently immutable
- Any change to the descriptor produces a new hash
- Both versions can coexist in the registry
- A new version requires a new `circuit_id` (bumped semver)

Example:
```
trade/import-landed-cost@1.0.0  -> hash_v1
trade/import-landed-cost@2.0.0  -> hash_v2
```

## Dataset Dependencies

If your circuit depends on external datasets, declare them:

```json
{
  "dataset_dependencies": [
    {
      "dataset_id": "cbp/hts-tariff-rules",
      "min_version": "2026.1.0",
      "description": "US Harmonized Tariff Schedule"
    }
  ]
}
```

**Format**: `<authority>/<name>`

**Common datasets**:
- `cbp/hts-tariff-rules` — US CBP tariff rules
- `fda/drug-interactions` — FDA drug interaction DB
- `treasury/ofac-sdn` — OFAC sanctions list
- `nih/evidence-guidelines` — NIH clinical guidelines

When verifying a proof bundle, the verifier must:

1. Retrieve the dataset version specified in the bundle
2. Hash it using the same method as the circuit
3. Verify the hash matches the commitment in the proof

## Proof Systems

Your circuit must support at least one of:

| Proof System | Use Case | Security | Hardware |
|--------------|----------|----------|----------|
| `plonk-halo2-pasta` | General-purpose ZK | Cryptographic | Any |
| `plonk-halo2-bn254` | High-throughput ZK | Cryptographic | Any |
| `groth16-bn254` | Compact proofs | Cryptographic | Any |
| `stark` | Post-quantum | Cryptographic | Any |
| `zk-ml` | ML inference | Cryptographic | GPU |
| `tee-intel-tdx` | Confidential VMs | Hardware | Intel |
| `tee-amd-sev-snp` | Confidential VMs | Hardware | AMD |
| `tee-aws-nitro` | Cloud enclaves | Hardware | AWS |
| `sha256-deterministic` | Deterministic compute | Hash-chain | Any |
| `api-hash-binding` | External APIs | Hash-binding | Any |

Choose based on:
- Performance requirements
- Security model (cryptographic vs. hardware)
- Available hardware/infrastructure
- Compatibility with downstream systems

## Examples

### Example 1: Simple EXPERIMENTAL Circuit

File: `circuits/general-example-1.0.0.json`

```json
{
  "circuit_id": "general/example@1.0.0",
  "spec_version": "vrl/circuit/1.0",
  "circuit_hash": "a1b2c3d4e5f6...",
  "domain": "general",
  "name": "example",
  "version": "1.0.0",
  "description": "Example circuit for demonstration",
  "input_schema": {
    "private": [
      {"name": "x", "type": "integer", "description": "Input value"}
    ],
    "public": [
      {"name": "y", "type": "integer", "description": "Public input"}
    ]
  },
  "output_schema": {
    "public": [
      {"name": "result", "type": "integer", "description": "Output"}
    ]
  },
  "proof_systems": ["plonk-halo2-pasta"],
  "constraint_count": 3,
  "certification_tier": "EXPERIMENTAL",
  "published_at": "2026-04-04T00:00:00Z",
  "author": "Jane Researcher",
  "author_email": "jane@example.com",
  "license": "Apache-2.0"
}
```

### Example 2: REVIEWED Circuit with Dependencies

See the `trade/import-landed-cost@1.0.0` circuit in the registry for a real example.

### Example 3: CERTIFIED Audited Circuit

See the `healthcare/clinical-decision-support@1.0.0` circuit for an example with formal audit report.

## Common Issues and FAQs

### Q: How do I update a circuit?

A: Create a new version. You cannot modify a published circuit — doing so would change the `circuit_hash`. Instead:

1. Bump the version: `1.0.0` -> `1.1.0`
2. Compute a new `circuit_hash`
3. Update `published_at` to the new submission date
4. Submit as a new circuit entry

Both versions will exist in the registry independently.

### Q: Can I deprecate a circuit?

A: Yes. In the descriptor, set `"deprecated": true`. The circuit remains in the registry for forensic purposes, but is marked as no longer recommended. New proofs should not reference deprecated circuits.

### Q: How do I handle dataset version changes?

A: If a dataset you depend on is updated (e.g., CBP tariff rules change), you should:

1. Test your circuit against the new dataset version
2. Update `min_version` if necessary
3. If major behavior changes, create a new circuit version

### Q: What if my circuit has no external dependencies?

A: Set `"dataset_dependencies": []` (empty array). This is valid for circuits that use only public inputs or built-in deterministic functions.

### Q: How large can a constraint count be?

A: There is no hard limit. However:
- Smaller circuits (< 100 constraints) are preferred for performance
- Very large circuits (> 10,000 constraints) may have slow proof generation
- Optimize your circuit design before publication

### Q: Can I use EXPERIMENTAL for production?

A: **Not recommended**. EXPERIMENTAL circuits have only automated validation, not security review. For production use, target REVIEWED or CERTIFIED tiers.

### Q: How long until my CERTIFIED circuit is audited?

A: Timeline depends on audit firm capacity:
- Trail of Bits: 4-8 weeks
- OpenZeppelin: 3-6 weeks
- Least Authority: 6-10 weeks

Contact VRL maintainers to arrange an audit.

## Compliance and Legal

### License

All circuit descriptors are published under **CC BY 4.0** (Creative Commons Attribution 4.0 International). You retain copyright but agree that others may use and modify with attribution.

The circuit **source code** may be licensed under any SPDX license (Apache, MIT, GPL, etc.). Specify in the descriptor.

### Regulatory Compliance

If your circuit is used in a regulated context (healthcare, finance), ensure:

- Compliance frameworks are declared in the descriptor
- All relevant audits are completed
- Data handling meets regulatory requirements
- Documentation supports regulatory arguments

## Support and Questions

- **Issues**: https://github.com/vrl-protocol/spec/issues
- **Discussions**: https://github.com/vrl-protocol/spec/discussions
- **Email**: registry@vrl-protocol.org

---

**Last Updated**: 2026-04-04
**Registry Version**: 1.0.0
