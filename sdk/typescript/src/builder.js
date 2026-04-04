/**
 * Fluent builder API for constructing VRL Proof Bundles.
 * Provides a convenient fluent interface for building complex bundles incrementally.
 */

const { computeIntegrityHash } = require("./hashing");

/**
 * Generates a UUIDv5-like bundle ID from an integrity hash.
 *
 * @param {string} integrityHash The integrity hash to derive from
 * @returns {string} A UUID-format string
 */
function generateBundleId(integrityHash) {
  // Use first 16 bytes of the integrity hash to seed a deterministic UUID-like string
  const bytes = Buffer.from(integrityHash.substring(0, 32), "hex");

  // Format as UUID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  let uuid = "";
  for (let i = 0; i < 16 && i < bytes.length; i++) {
    uuid += bytes[i].toString(16).padStart(2, "0");
    if (i === 3 || i === 5 || i === 7 || i === 9) {
      uuid += "-";
    }
  }

  return uuid;
}

/**
 * Fluent builder for constructing VRL Proof Bundles.
 */
class ProofBundleBuilder {
  constructor() {
    this.vrlVersion = "1.0";
    this.bundleId = null;
    this.issuedAt = null;
    this.aiIdentity = null;
    this.computation = null;
    this.proof = null;
    this.dataCommitments = [];
    this.legal = null;
    this.proofGraph = null;
    this.trustContext = null;
  }

  setVrlVersion(version) {
    this.vrlVersion = version;
    return this;
  }

  setBundleId(bundleId) {
    this.bundleId = bundleId;
    return this;
  }

  setIssuedAt(issuedAt) {
    this.issuedAt = issuedAt;
    return this;
  }

  setIssuedAtNow() {
    const now = new Date();
    this.issuedAt = now.toISOString();
    return this;
  }

  setAIIdentity(aiIdentity) {
    this.aiIdentity = aiIdentity;
    return this;
  }

  setComputation(computation) {
    this.computation = computation;
    return this;
  }

  setProof(proof) {
    this.proof = proof;
    return this;
  }

  addDataCommitment(commitment) {
    this.dataCommitments.push(commitment);
    return this;
  }

  setLegal(legal) {
    this.legal = legal;
    return this;
  }

  setProofGraph(proofGraph) {
    this.proofGraph = proofGraph;
    return this;
  }

  setTrustContext(trustContext) {
    this.trustContext = trustContext;
    return this;
  }

  build() {
    // Check required fields
    if (this.aiIdentity === null) {
      throw new Error("ai_identity is required");
    }
    if (this.computation === null) {
      throw new Error("computation is required");
    }
    if (this.proof === null) {
      throw new Error("proof is required");
    }

    // Set issued_at if not provided
    if (this.issuedAt === null) {
      this.setIssuedAtNow();
    }

    // Compute bundle_id if not provided
    if (this.bundleId === null) {
      this.bundleId = generateBundleId(this.computation.integrity_hash);
    }

    const bundle = {
      vrl_version: this.vrlVersion,
      bundle_id: this.bundleId,
      issued_at: this.issuedAt,
      ai_identity: this.aiIdentity,
      computation: this.computation,
      proof: this.proof,
    };

    if (this.dataCommitments.length > 0) {
      bundle.data_commitments = this.dataCommitments;
    }

    if (this.legal !== null) {
      bundle.legal = this.legal;
    }

    if (this.proofGraph !== null) {
      bundle.proof_graph = this.proofGraph;
    }

    if (this.trustContext !== null) {
      bundle.trust_context = this.trustContext;
    }

    return bundle;
  }
}

/**
 * Fluent builder for constructing Computation objects.
 */
class ComputationBuilder {
  constructor() {
    this.circuitId = null;
    this.circuitVersion = null;
    this.circuitHash = null;
    this.inputHash = null;
    this.outputHash = null;
    this.traceHash = null;
    this.integrityHash = null;
  }

  setCircuitId(circuitId) {
    this.circuitId = circuitId;
    return this;
  }

  setCircuitVersion(version) {
    this.circuitVersion = version;
    return this;
  }

  setCircuitHash(hashValue) {
    this.circuitHash = hashValue;
    return this;
  }

  setInputHash(hashValue) {
    this.inputHash = hashValue;
    return this;
  }

  setOutputHash(hashValue) {
    this.outputHash = hashValue;
    return this;
  }

  setTraceHash(hashValue) {
    this.traceHash = hashValue;
    return this;
  }

  setIntegrityHash(hashValue) {
    this.integrityHash = hashValue;
    return this;
  }

  computeIntegrityHash() {
    if (
      this.inputHash === null ||
      this.outputHash === null ||
      this.traceHash === null
    ) {
      throw new Error(
        "Must set input_hash, output_hash, and trace_hash first"
      );
    }
    this.integrityHash = computeIntegrityHash(
      this.inputHash,
      this.outputHash,
      this.traceHash
    );
    return this;
  }

  build() {
    const missingFields = [];
    if (this.circuitId === null) missingFields.push("circuit_id");
    if (this.circuitVersion === null) missingFields.push("circuit_version");
    if (this.circuitHash === null) missingFields.push("circuit_hash");
    if (this.inputHash === null) missingFields.push("input_hash");
    if (this.outputHash === null) missingFields.push("output_hash");
    if (this.traceHash === null) missingFields.push("trace_hash");
    if (this.integrityHash === null) missingFields.push("integrity_hash");

    if (missingFields.length > 0) {
      throw new Error(
        `Missing required computation fields: ${missingFields.join(", ")}`
      );
    }

    return {
      circuit_id: this.circuitId,
      circuit_version: this.circuitVersion,
      circuit_hash: this.circuitHash,
      input_hash: this.inputHash,
      output_hash: this.outputHash,
      trace_hash: this.traceHash,
      integrity_hash: this.integrityHash,
    };
  }
}

/**
 * Fluent builder for constructing Proof objects.
 */
class ProofBuilder {
  constructor() {
    this.proofSystem = null;
    this.proofBytes = null;
    this.publicInputs = null;
    this.verificationKeyId = null;
    this.proofHash = null;
    this.commitments = null;
  }

  setProofSystem(system) {
    this.proofSystem = system;
    return this;
  }

  setProofBytes(proofBytes) {
    this.proofBytes = proofBytes;
    return this;
  }

  setPublicInputs(inputs) {
    this.publicInputs = inputs;
    return this;
  }

  setVerificationKeyId(keyId) {
    this.verificationKeyId = keyId;
    return this;
  }

  setProofHash(hashValue) {
    this.proofHash = hashValue;
    return this;
  }

  setCommitments(commitments) {
    this.commitments = commitments;
    return this;
  }

  build() {
    const missingFields = [];
    if (this.proofSystem === null) missingFields.push("proof_system");
    if (this.proofBytes === null) missingFields.push("proof_bytes");
    if (this.publicInputs === null) missingFields.push("public_inputs");
    if (this.verificationKeyId === null) missingFields.push("verification_key_id");
    if (this.proofHash === null) missingFields.push("proof_hash");

    if (missingFields.length > 0) {
      throw new Error(
        `Missing required proof fields: ${missingFields.join(", ")}`
      );
    }

    const proof = {
      proof_system: this.proofSystem,
      proof_bytes: this.proofBytes,
      public_inputs: this.publicInputs,
      verification_key_id: this.verificationKeyId,
      proof_hash: this.proofHash,
    };

    if (this.commitments !== null) {
      proof.commitments = this.commitments;
    }

    return proof;
  }
}

module.exports = {
  ProofBundleBuilder,
  ComputationBuilder,
  ProofBuilder,
};
