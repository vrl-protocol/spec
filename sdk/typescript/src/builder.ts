/**
 * Fluent builder API for constructing VRL Proof Bundles.
 * Provides a convenient fluent interface for building complex bundles incrementally.
 */

import { randomUUID } from "crypto";
import {
  ProofBundle,
  AIIdentity,
  Computation,
  Proof,
  DataCommitment,
  Legal,
  ProofGraph,
  TrustContext,
} from "./types";
import { computeIntegrityHash } from "./hashing";

/**
 * Generates a UUIDv5-like bundle ID from an integrity hash.
 *
 * Note: Since Node.js crypto doesn't have native UUIDv5 support,
 * we use UUIDv4 for deterministic generation in this implementation.
 * In production, users should pre-compute bundle IDs using the hash.
 *
 * @param integrityHash The integrity hash to derive from
 * @returns A UUID-format string
 */
function generateBundleId(integrityHash: string): string {
  // Use first 16 bytes of the integrity hash to seed a deterministic UUID-like string
  // This maintains bundle_id stability based on integrity_hash
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
 *
 * Example usage:
 * ```typescript
 * const bundle = new ProofBundleBuilder()
 *   .setAIIdentity(identity)
 *   .setComputation(computation)
 *   .setProof(proof)
 *   .setLegal(legal)
 *   .build();
 * ```
 */
export class ProofBundleBuilder {
  private vrlVersion: string = "1.0";
  private bundleId: string | null = null;
  private issuedAt: string | null = null;
  private aiIdentity: AIIdentity | null = null;
  private computation: Computation | null = null;
  private proof: Proof | null = null;
  private dataCommitments: DataCommitment[] = [];
  private legal: Legal | null = null;
  private proofGraph: ProofGraph | null = null;
  private trustContext: TrustContext | null = null;

  /**
   * Set VRL specification version (default: "1.0").
   *
   * @param version VRL spec version
   * @returns Self for chaining
   */
  setVrlVersion(version: string): ProofBundleBuilder {
    this.vrlVersion = version;
    return this;
  }

  /**
   * Set bundle_id explicitly (normally computed from integrity_hash).
   *
   * @param bundleId UUID string
   * @returns Self for chaining
   */
  setBundleId(bundleId: string): ProofBundleBuilder {
    this.bundleId = bundleId;
    return this;
  }

  /**
   * Set issued_at timestamp (RFC 3339 format).
   *
   * @param issuedAt RFC 3339 timestamp (e.g. "2026-04-04T12:00:00.000Z")
   * @returns Self for chaining
   */
  setIssuedAt(issuedAt: string): ProofBundleBuilder {
    this.issuedAt = issuedAt;
    return this;
  }

  /**
   * Set issued_at to current UTC time.
   *
   * @returns Self for chaining
   */
  setIssuedAtNow(): ProofBundleBuilder {
    const now = new Date();
    this.issuedAt = now.toISOString();
    return this;
  }

  /**
   * Set the AI identity claim.
   *
   * @param aiIdentity AIIdentity instance
   * @returns Self for chaining
   */
  setAIIdentity(aiIdentity: AIIdentity): ProofBundleBuilder {
    this.aiIdentity = aiIdentity;
    return this;
  }

  /**
   * Set the computation record with hashes.
   *
   * @param computation Computation instance
   * @returns Self for chaining
   */
  setComputation(computation: Computation): ProofBundleBuilder {
    this.computation = computation;
    return this;
  }

  /**
   * Set the cryptographic proof.
   *
   * @param proof Proof instance
   * @returns Self for chaining
   */
  setProof(proof: Proof): ProofBundleBuilder {
    this.proof = proof;
    return this;
  }

  /**
   * Add a data commitment.
   *
   * @param commitment DataCommitment instance
   * @returns Self for chaining
   */
  addDataCommitment(commitment: DataCommitment): ProofBundleBuilder {
    this.dataCommitments.push(commitment);
    return this;
  }

  /**
   * Set legal metadata and compliance claims.
   *
   * @param legal Legal instance
   * @returns Self for chaining
   */
  setLegal(legal: Legal): ProofBundleBuilder {
    this.legal = legal;
    return this;
  }

  /**
   * Set proof graph for causal dependencies.
   *
   * @param proofGraph ProofGraph instance
   * @returns Self for chaining
   */
  setProofGraph(proofGraph: ProofGraph): ProofBundleBuilder {
    this.proofGraph = proofGraph;
    return this;
  }

  /**
   * Set trust context with trust score and anomaly flags.
   *
   * @param trustContext TrustContext instance
   * @returns Self for chaining
   */
  setTrustContext(trustContext: TrustContext): ProofBundleBuilder {
    this.trustContext = trustContext;
    return this;
  }

  /**
   * Build and return the ProofBundle.
   *
   * @returns ProofBundle instance
   * @throws Error If required fields are not set
   */
  build(): ProofBundle {
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

    const bundle: ProofBundle = {
      vrl_version: this.vrlVersion,
      bundle_id: this.bundleId,
      issued_at: this.issuedAt!,
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
export class ComputationBuilder {
  private circuitId: string | null = null;
  private circuitVersion: string | null = null;
  private circuitHash: string | null = null;
  private inputHash: string | null = null;
  private outputHash: string | null = null;
  private traceHash: string | null = null;
  private integrityHash: string | null = null;

  /**
   * Set circuit registry identifier.
   *
   * @param circuitId Circuit ID
   * @returns Self for chaining
   */
  setCircuitId(circuitId: string): ComputationBuilder {
    this.circuitId = circuitId;
    return this;
  }

  /**
   * Set circuit semantic version.
   *
   * @param version Circuit version
   * @returns Self for chaining
   */
  setCircuitVersion(version: string): ComputationBuilder {
    this.circuitVersion = version;
    return this;
  }

  /**
   * Set circuit hash (SHA-256 hex).
   *
   * @param hashValue Hash value
   * @returns Self for chaining
   */
  setCircuitHash(hashValue: string): ComputationBuilder {
    this.circuitHash = hashValue;
    return this;
  }

  /**
   * Set input hash (SHA-256 hex).
   *
   * @param hashValue Hash value
   * @returns Self for chaining
   */
  setInputHash(hashValue: string): ComputationBuilder {
    this.inputHash = hashValue;
    return this;
  }

  /**
   * Set output hash (SHA-256 hex).
   *
   * @param hashValue Hash value
   * @returns Self for chaining
   */
  setOutputHash(hashValue: string): ComputationBuilder {
    this.outputHash = hashValue;
    return this;
  }

  /**
   * Set trace hash (SHA-256 hex).
   *
   * @param hashValue Hash value
   * @returns Self for chaining
   */
  setTraceHash(hashValue: string): ComputationBuilder {
    this.traceHash = hashValue;
    return this;
  }

  /**
   * Set integrity hash (SHA-256 hex).
   *
   * @param hashValue Hash value
   * @returns Self for chaining
   */
  setIntegrityHash(hashValue: string): ComputationBuilder {
    this.integrityHash = hashValue;
    return this;
  }

  /**
   * Compute integrity_hash from input, output, and trace hashes.
   *
   * @returns Self for chaining
   * @throws Error if input, output, or trace hashes are not set
   */
  computeIntegrityHash(): ComputationBuilder {
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

  /**
   * Build and return the Computation.
   *
   * @returns Computation instance
   * @throws Error If required fields are not set
   */
  build(): Computation {
    const missingFields: string[] = [];
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
export class ProofBuilder {
  private proofSystem: string | null = null;
  private proofBytes: string | null = null;
  private publicInputs: string[] | null = null;
  private verificationKeyId: string | null = null;
  private proofHash: string | null = null;
  private commitments: string[] | null = null;

  /**
   * Set proof system identifier.
   *
   * @param system Proof system ID
   * @returns Self for chaining
   */
  setProofSystem(system: string): ProofBuilder {
    this.proofSystem = system;
    return this;
  }

  /**
   * Set hex-encoded proof bytes.
   *
   * @param proofBytes Proof bytes
   * @returns Self for chaining
   */
  setProofBytes(proofBytes: string): ProofBuilder {
    this.proofBytes = proofBytes;
    return this;
  }

  /**
   * Set array of hex-encoded public inputs.
   *
   * @param inputs Public inputs
   * @returns Self for chaining
   */
  setPublicInputs(inputs: string[]): ProofBuilder {
    this.publicInputs = inputs;
    return this;
  }

  /**
   * Set verification key ID (SHA-256 hex).
   *
   * @param keyId Verification key ID
   * @returns Self for chaining
   */
  setVerificationKeyId(keyId: string): ProofBuilder {
    this.verificationKeyId = keyId;
    return this;
  }

  /**
   * Set proof hash (SHA-256 hex).
   *
   * @param hashValue Hash value
   * @returns Self for chaining
   */
  setProofHash(hashValue: string): ProofBuilder {
    this.proofHash = hashValue;
    return this;
  }

  /**
   * Set optional commitments array.
   *
   * @param commitments Commitments
   * @returns Self for chaining
   */
  setCommitments(commitments: string[]): ProofBuilder {
    this.commitments = commitments;
    return this;
  }

  /**
   * Build and return the Proof.
   *
   * @returns Proof instance
   * @throws Error If required fields are not set
   */
  build(): Proof {
    const missingFields: string[] = [];
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

    const proof: Proof = {
      proof_system: this.proofSystem as any,
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
