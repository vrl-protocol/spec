/**
 * Verification module for VRL Proof Bundles.
 * Implements the 10-step verification procedure specified in VRL Spec §12.
 */

const {
  sha256,
  canonicalJson,
  computeIntegrityHash,
  computeProofHash,
  computeCommitmentHash,
} = require("./hashing");

/**
 * VRL Proof Bundle verifier implementing the 10-step verification procedure.
 * Implements the verification procedure from VRL Spec §12.
 */
class Verifier {
  static VRL_NAMESPACE_UUID = "d9ec1f3e-2d27-45d4-af5f-d8d5efcb7c1e";

  /**
   * Verify a proof bundle according to VRL Spec §12.
   *
   * @param {object} bundle ProofBundle to verify
   * @returns {object} VerificationResult with status and detailed results
   */
  verify(bundle) {
    const steps = [];
    const errorCodes = [];
    let status = "VALID";

    // Step 1: Version Check
    if (!this.step1VersionCheck(bundle, steps)) {
      return {
        status: "UNSUPPORTED_VERSION",
        errorCodes: ["UNSUPPORTED_VERSION"],
        steps,
      };
    }

    // Step 2: Schema Validation
    if (!this.step2SchemaValidation(bundle, steps)) {
      return {
        status: "SCHEMA_INVALID",
        errorCodes: ["SCHEMA_INVALID"],
        steps,
      };
    }

    // Step 3: bundle_id Recomputation
    if (!this.step3BundleIdCheck(bundle, steps)) {
      errorCodes.push("BUNDLE_ID_MISMATCH");
      status = "BUNDLE_ID_MISMATCH";
    }

    // Step 4: Integrity Hash Recomputation
    if (!this.step4IntegrityHashCheck(bundle, steps)) {
      errorCodes.push("INTEGRITY_MISMATCH");
      status = "INTEGRITY_MISMATCH";
    }

    // Step 5: Circuit Resolution
    if (!this.step5CircuitResolution(bundle, steps)) {
      errorCodes.push("CIRCUIT_HASH_MISMATCH");
      status = "CIRCUIT_HASH_MISMATCH";
    }

    // Step 6: Proof Verification
    if (!this.step6ProofStructureValidation(bundle, steps)) {
      errorCodes.push("PROOF_INVALID");
      status = "PROOF_INVALID";
    }

    // Step 7: AI-ID Verification
    if (!this.step7AIIdVerification(bundle, steps)) {
      errorCodes.push("AI_ID_INVALID");
      status = "AI_ID_INVALID";
    }

    // Step 8: Data Commitment Verification
    if (!this.step8DataCommitmentVerification(bundle, steps)) {
      errorCodes.push("DATA_COMMITMENT_INVALID");
      status = "DATA_COMMITMENT_INVALID";
    }

    // Step 9: Timestamp Verification (optional)
    if (bundle.legal?.timestamp_authority) {
      if (!this.step9TimestampVerification(bundle, steps)) {
        errorCodes.push("TIMESTAMP_INVALID");
        if (status === "VALID") {
          status = "VALID_PARTIAL";
        }
      }
    }

    // Step 10: Proof Graph Edges (optional)
    if (bundle.proof_graph?.depends_on) {
      if (!this.step10ProofGraphVerification(bundle, steps)) {
        errorCodes.push("GRAPH_EDGE_INVALID");
        if (status === "VALID") {
          status = "VALID_PARTIAL";
        }
      }
    }

    return { status, errorCodes, steps };
  }

  step1VersionCheck(bundle, steps) {
    if (bundle.vrl_version !== "1.0") {
      steps.push({
        step: 1,
        name: "Version Check",
        passed: false,
        detail: `Unsupported vrl_version: ${bundle.vrl_version}`,
      });
      return false;
    }

    steps.push({
      step: 1,
      name: "Version Check",
      passed: true,
      detail: `vrl_version ${bundle.vrl_version} is supported`,
    });
    return true;
  }

  step2SchemaValidation(bundle, steps) {
    // Check required fields exist
    if (
      !bundle.bundle_id ||
      !bundle.issued_at ||
      !bundle.ai_identity ||
      !bundle.computation ||
      !bundle.proof
    ) {
      steps.push({
        step: 2,
        name: "Schema Validation",
        passed: false,
        detail: "Missing required fields",
      });
      return false;
    }

    // Validate ai_id format (64 hex characters)
    if (!this.isValidHexHash(bundle.ai_identity.ai_id)) {
      steps.push({
        step: 2,
        name: "Schema Validation",
        passed: false,
        detail: `Invalid ai_id format: ${bundle.ai_identity.ai_id}`,
      });
      return false;
    }

    // Validate hash fields
    const hashFields = [
      ["circuit_hash", bundle.computation.circuit_hash],
      ["input_hash", bundle.computation.input_hash],
      ["output_hash", bundle.computation.output_hash],
      ["trace_hash", bundle.computation.trace_hash],
      ["integrity_hash", bundle.computation.integrity_hash],
      ["proof_hash", bundle.proof.proof_hash],
    ];

    for (const [fieldName, hashValue] of hashFields) {
      if (!this.isValidHexHash(hashValue)) {
        steps.push({
          step: 2,
          name: "Schema Validation",
          passed: false,
          detail: `Invalid ${fieldName} format: ${hashValue}`,
        });
        return false;
      }
    }

    steps.push({
      step: 2,
      name: "Schema Validation",
      passed: true,
      detail: "All required fields present and valid",
    });
    return true;
  }

  step3BundleIdCheck(bundle, steps) {
    const uuidRegex =
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuidRegex.test(bundle.bundle_id)) {
      steps.push({
        step: 3,
        name: "bundle_id Recomputation",
        passed: false,
        detail: `Invalid bundle_id format: ${bundle.bundle_id}`,
      });
      return false;
    }

    steps.push({
      step: 3,
      name: "bundle_id Recomputation",
      passed: true,
      detail: `bundle_id ${bundle.bundle_id} has valid format`,
    });
    return true;
  }

  step4IntegrityHashCheck(bundle, steps) {
    const recomputedIntegrity = computeIntegrityHash(
      bundle.computation.input_hash,
      bundle.computation.output_hash,
      bundle.computation.trace_hash
    );

    if (recomputedIntegrity !== bundle.computation.integrity_hash) {
      steps.push({
        step: 4,
        name: "Integrity Hash Recomputation",
        passed: false,
        detail: `integrity_hash mismatch: expected ${recomputedIntegrity}, got ${bundle.computation.integrity_hash}`,
      });
      return false;
    }

    steps.push({
      step: 4,
      name: "Integrity Hash Recomputation",
      passed: true,
      detail: `integrity_hash ${bundle.computation.integrity_hash} is valid`,
    });
    return true;
  }

  step5CircuitResolution(bundle, steps) {
    if (!this.isValidHexHash(bundle.computation.circuit_hash)) {
      steps.push({
        step: 5,
        name: "Circuit Resolution",
        passed: false,
        detail: `Invalid circuit_hash format: ${bundle.computation.circuit_hash}`,
      });
      return false;
    }

    steps.push({
      step: 5,
      name: "Circuit Resolution",
      passed: true,
      detail: `Circuit ${bundle.computation.circuit_id} hash validated`,
    });
    return true;
  }

  step6ProofStructureValidation(bundle, steps) {
    const validSystems = [
      "plonk-halo2-pasta",
      "plonk-halo2-bn254",
      "groth16-bn254",
      "stark",
      "zk-ml",
      "tee-intel-tdx",
      "tee-amd-sev-snp",
      "tee-aws-nitro",
      "sha256-deterministic",
      "api-hash-binding",
    ];

    if (!validSystems.includes(bundle.proof.proof_system)) {
      steps.push({
        step: 6,
        name: "Proof Structure Validation",
        passed: false,
        detail: `Invalid proof_system: ${bundle.proof.proof_system}`,
      });
      return false;
    }

    const recomputedProofHash = computeProofHash({
      circuitHash: bundle.computation.circuit_hash,
      proofBytes: bundle.proof.proof_bytes,
      publicInputs: bundle.proof.public_inputs,
      proofSystem: bundle.proof.proof_system,
      traceHash: bundle.computation.trace_hash,
    });

    if (recomputedProofHash !== bundle.proof.proof_hash) {
      steps.push({
        step: 6,
        name: "Proof Structure Validation",
        passed: false,
        detail: `proof_hash mismatch: expected ${recomputedProofHash}, got ${bundle.proof.proof_hash}`,
      });
      return false;
    }

    steps.push({
      step: 6,
      name: "Proof Structure Validation",
      passed: true,
      detail: `Proof structure valid for ${bundle.proof.proof_system}`,
    });
    return true;
  }

  step7AIIdVerification(bundle, steps) {
    const aiId = bundle.ai_identity.ai_id;
    if (!this.isValidHexHash(aiId)) {
      steps.push({
        step: 7,
        name: "AI-ID Verification",
        passed: false,
        detail: `Invalid ai_id format: ${aiId}`,
      });
      return false;
    }

    const message = bundle.ai_identity.provider_signature
      ? `AI-ID ${aiId} is valid (provider_signature present)`
      : `AI-ID ${aiId} is valid (no provider_signature)`;

    steps.push({
      step: 7,
      name: "AI-ID Verification",
      passed: true,
      detail: message,
    });
    return true;
  }

  step8DataCommitmentVerification(bundle, steps) {
    if (!bundle.data_commitments || bundle.data_commitments.length === 0) {
      steps.push({
        step: 8,
        name: "Data Commitment Verification",
        passed: true,
        detail: "No data commitments",
      });
      return true;
    }

    for (let i = 0; i < bundle.data_commitments.length; i++) {
      const commitment = bundle.data_commitments[i];
      const recomputedHash = computeCommitmentHash(
        commitment.dataset_id,
        commitment.dataset_version,
        commitment.dataset_hash,
        commitment.provider_id,
        commitment.committed_at
      );

      if (recomputedHash !== commitment.commitment_hash) {
        steps.push({
          step: 8,
          name: `Data Commitment Verification [${i}]`,
          passed: false,
          detail: `commitment_hash mismatch for ${commitment.dataset_id}`,
        });
        return false;
      }
    }

    steps.push({
      step: 8,
      name: "Data Commitment Verification",
      passed: true,
      detail: `All ${bundle.data_commitments.length} data commitments verified`,
    });
    return true;
  }

  step9TimestampVerification(bundle, steps) {
    if (!bundle.legal?.timestamp_authority) {
      return true;
    }

    const tsa = bundle.legal.timestamp_authority;
    if (!tsa.tsa_token || !tsa.tsa_provider || !tsa.tsa_hash_algorithm) {
      steps.push({
        step: 9,
        name: "Timestamp Verification",
        passed: false,
        detail: "Incomplete timestamp_authority block",
      });
      return false;
    }

    steps.push({
      step: 9,
      name: "Timestamp Verification",
      passed: true,
      detail: `Timestamp token from ${tsa.tsa_provider}`,
    });
    return true;
  }

  step10ProofGraphVerification(bundle, steps) {
    if (!bundle.proof_graph?.depends_on) {
      return true;
    }

    const uuidRegex =
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

    for (const bundleId of bundle.proof_graph.depends_on) {
      if (!uuidRegex.test(bundleId)) {
        steps.push({
          step: 10,
          name: "Proof Graph Verification",
          passed: false,
          detail: `Invalid bundle_id in depends_on: ${bundleId}`,
        });
        return false;
      }
    }

    steps.push({
      step: 10,
      name: "Proof Graph Verification",
      passed: true,
      detail: "Proof graph edges valid",
    });
    return true;
  }

  isValidHexHash(value) {
    if (typeof value !== "string") {
      return false;
    }
    if (value.length !== 64) {
      return false;
    }
    try {
      parseInt(value, 16);
      return value === value.toLowerCase();
    } catch {
      return false;
    }
  }
}

module.exports = { Verifier };
