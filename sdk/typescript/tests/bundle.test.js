/**
 * Tests for VRL SDK using Node.js built-in test module.
 */

const { test } = require("node:test");
const assert = require("node:assert");
const {
  ProofBundleBuilder,
  ComputationBuilder,
  ProofBuilder,
  Verifier,
  parseBundle,
  serializeBundle,
  computeIntegrityHash,
  computeProofHash,
  computeCommitmentHash,
  sha256,
  canonicalJson,
} = require("../src/index");

// Helper function to create a minimal valid bundle
function createValidBundle() {
  const aiIdentity = {
    ai_id: "a".repeat(64),
    provider_id: "com.test",
    model_name: "test-model",
    model_version: "1.0.0",
    model_weights_hash: "b".repeat(64),
    runtime_hash: "c".repeat(64),
    config_hash: "d".repeat(64),
  };

  const computation = new ComputationBuilder()
    .setCircuitId("test/circuit@1.0.0")
    .setCircuitVersion("1.0.0")
    .setCircuitHash("e".repeat(64))
    .setInputHash("f".repeat(64))
    .setOutputHash("0".repeat(64))
    .setTraceHash("1".repeat(64))
    .computeIntegrityHash()
    .build();

  // Compute correct proof hash based on the computation
  const proofHashValue = computeProofHash({
    circuitHash: computation.circuit_hash,
    proofBytes: "2".repeat(128),
    publicInputs: ["3".repeat(64)],
    proofSystem: "sha256-deterministic",
    traceHash: computation.trace_hash,
  });

  const proof = new ProofBuilder()
    .setProofSystem("sha256-deterministic")
    .setProofBytes("2".repeat(128))
    .setPublicInputs(["3".repeat(64)])
    .setVerificationKeyId("4".repeat(64))
    .setProofHash(proofHashValue)
    .build();

  const bundle = new ProofBundleBuilder()
    .setAIIdentity(aiIdentity)
    .setComputation(computation)
    .setProof(proof)
    .build();

  return bundle;
}

test("Hash utilities - canonicalJson", () => {
  const obj = { z: 1, a: 2, m: [1, 2, 3] };
  const result = canonicalJson(obj);
  assert.strictEqual(result, '{"a":2,"m":[1,2,3],"z":1}');
});

test("Hash utilities - sha256", () => {
  const hash = sha256("test");
  assert.strictEqual(hash.length, 64);
  assert.strictEqual(hash, hash.toLowerCase());
  assert.match(hash, /^[0-9a-f]{64}$/);
});

test("Hash utilities - computeIntegrityHash", () => {
  const input = "a".repeat(64);
  const output = "b".repeat(64);
  const trace = "c".repeat(64);
  const integrity = computeIntegrityHash(input, output, trace);
  assert.strictEqual(integrity.length, 64);
  assert.match(integrity, /^[0-9a-f]{64}$/);
});

test("Hash utilities - computeProofHash", () => {
  const proofHash = computeProofHash({
    circuitHash: "a".repeat(64),
    proofBytes: "b".repeat(128),
    publicInputs: ["c".repeat(64)],
    proofSystem: "sha256-deterministic",
    traceHash: "d".repeat(64),
  });
  assert.strictEqual(proofHash.length, 64);
  assert.match(proofHash, /^[0-9a-f]{64}$/);
});

test("Hash utilities - computeCommitmentHash", () => {
  const commitment = computeCommitmentHash(
    "dataset1",
    "1.0.0",
    "e".repeat(64),
    "provider",
    "2026-04-04T00:00:00Z"
  );
  assert.strictEqual(commitment.length, 64);
  assert.match(commitment, /^[0-9a-f]{64}$/);
});

test("Builder - ComputationBuilder", () => {
  const comp = new ComputationBuilder()
    .setCircuitId("test/circuit")
    .setCircuitVersion("1.0.0")
    .setCircuitHash("a".repeat(64))
    .setInputHash("b".repeat(64))
    .setOutputHash("c".repeat(64))
    .setTraceHash("d".repeat(64))
    .computeIntegrityHash()
    .build();

  assert.strictEqual(comp.circuit_id, "test/circuit");
  assert.strictEqual(comp.circuit_version, "1.0.0");
  assert.match(comp.integrity_hash, /^[0-9a-f]{64}$/);
});

test("Builder - ProofBuilder", () => {
  const proof = new ProofBuilder()
    .setProofSystem("plonk-halo2-bn254")
    .setProofBytes("abcd")
    .setPublicInputs(["ef01"])
    .setVerificationKeyId("a".repeat(64))
    .setProofHash("b".repeat(64))
    .build();

  assert.strictEqual(proof.proof_system, "plonk-halo2-bn254");
  assert.deepStrictEqual(proof.public_inputs, ["ef01"]);
});

test("Builder - ProofBundleBuilder", () => {
  const bundle = createValidBundle();

  assert.strictEqual(bundle.vrl_version, "1.0");
  assert.match(bundle.bundle_id, /^[0-9a-f-]+$/);
  assert.ok(bundle.issued_at);
  assert.strictEqual(bundle.ai_identity.provider_id, "com.test");
});

test("Builder - ProofBundleBuilder with data commitment", () => {
  const bundle = new ProofBundleBuilder()
    .setAIIdentity({
      ai_id: "a".repeat(64),
      provider_id: "com.test",
      model_name: "test",
      model_version: "1.0.0",
      model_weights_hash: "b".repeat(64),
      runtime_hash: "c".repeat(64),
      config_hash: "d".repeat(64),
    })
    .setComputation(
      new ComputationBuilder()
        .setCircuitId("test/circuit")
        .setCircuitVersion("1.0.0")
        .setCircuitHash("e".repeat(64))
        .setInputHash("f".repeat(64))
        .setOutputHash("0".repeat(64))
        .setTraceHash("1".repeat(64))
        .computeIntegrityHash()
        .build()
    )
    .setProof(
      new ProofBuilder()
        .setProofSystem("sha256-deterministic")
        .setProofBytes("2".repeat(128))
        .setPublicInputs(["3".repeat(64)])
        .setVerificationKeyId("4".repeat(64))
        .setProofHash("5".repeat(64))
        .build()
    )
    .addDataCommitment({
      dataset_id: "dataset1",
      dataset_version: "1.0.0",
      dataset_hash: "6".repeat(64),
      provider_id: "provider",
      committed_at: "2026-04-04T00:00:00Z",
      commitment_hash: computeCommitmentHash(
        "dataset1",
        "1.0.0",
        "6".repeat(64),
        "provider",
        "2026-04-04T00:00:00Z"
      ),
    })
    .build();

  assert.ok(bundle.data_commitments);
  assert.strictEqual(bundle.data_commitments.length, 1);
  assert.strictEqual(bundle.data_commitments[0].dataset_id, "dataset1");
});

test("Bundle - serialize and deserialize round-trip", () => {
  const original = createValidBundle();
  const serialized = serializeBundle(original);
  const deserialized = parseBundle(serialized);

  assert.strictEqual(deserialized.bundle_id, original.bundle_id);
  assert.strictEqual(deserialized.vrl_version, original.vrl_version);
  assert.strictEqual(deserialized.ai_identity.ai_id, original.ai_identity.ai_id);
  assert.strictEqual(
    deserialized.computation.circuit_id,
    original.computation.circuit_id
  );
});

test("Verifier - verify valid bundle", () => {
  const bundle = createValidBundle();
  const verifier = new Verifier();
  const result = verifier.verify(bundle);

  assert.ok(result.status === "VALID");
  assert.strictEqual(result.errorCodes.length, 0);
  assert.ok(result.steps.length > 0);

  // Check that all steps passed
  for (const step of result.steps) {
    assert.ok(step.passed, `Step ${step.name} should have passed`);
  }
});

test("Verifier - reject bundle with tampered integrity_hash", () => {
  const bundle = createValidBundle();
  bundle.computation.integrity_hash = "a".repeat(64); // tamper with hash

  const verifier = new Verifier();
  const result = verifier.verify(bundle);

  assert.ok(result.status !== "VALID");
  assert.ok(result.errorCodes.includes("INTEGRITY_MISMATCH"));
});

test("Verifier - reject bundle with invalid proof_hash", () => {
  const bundle = createValidBundle();
  bundle.proof.proof_hash = "z".repeat(64); // tamper with proof hash

  const verifier = new Verifier();
  const result = verifier.verify(bundle);

  assert.ok(result.status !== "VALID");
  assert.ok(result.errorCodes.includes("PROOF_INVALID"));
});

test("Verifier - reject bundle with unsupported version", () => {
  const bundle = createValidBundle();
  bundle.vrl_version = "2.0";

  const verifier = new Verifier();
  const result = verifier.verify(bundle);

  assert.strictEqual(result.status, "UNSUPPORTED_VERSION");
  assert.ok(result.errorCodes.includes("UNSUPPORTED_VERSION"));
});

test("Verifier - verify bundle with proof graph", () => {
  const bundle = createValidBundle();
  bundle.proof_graph = {
    depends_on: ["12345678-1234-1234-1234-123456789012"],
  };

  const verifier = new Verifier();
  const result = verifier.verify(bundle);

  assert.strictEqual(result.status, "VALID");
});

test("Builder - throw on missing required fields", () => {
  const builder = new ProofBundleBuilder();
  assert.throws(
    () => builder.build(),
    /ai_identity is required/
  );
});

test("Builder - ComputationBuilder throw on missing integrity hash inputs", () => {
  const builder = new ComputationBuilder()
    .setCircuitId("test")
    .setCircuitVersion("1.0");

  assert.throws(
    () => builder.computeIntegrityHash(),
    /Must set input_hash/
  );
});

test("Bundle - parseBundle throws on invalid JSON", () => {
  assert.throws(() => parseBundle("not json"), /Invalid JSON/);
});

test("Bundle - parseBundle throws on missing required fields", () => {
  assert.throws(() => parseBundle('{"vrl_version":"1.0"}'), /Missing required field/);
});
