/**
 * TypeScript types for VRL Proof Bundles.
 * Implements the complete schema specified in VRL Spec §3 and §17.
 */

/**
 * Valid proof system identifiers.
 * From VRL Spec §3.7
 */
export type ProofSystem =
  | "plonk-halo2-pasta"
  | "plonk-halo2-bn254"
  | "groth16-bn254"
  | "stark"
  | "zk-ml"
  | "tee-intel-tdx"
  | "tee-amd-sev-snp"
  | "tee-aws-nitro"
  | "sha256-deterministic"
  | "api-hash-binding";

/**
 * Circuit certification tiers.
 * From VRL Spec §9
 */
export type CertificationTier =
  | "tier-1-unvetted"
  | "tier-2-community-tested"
  | "tier-3-formally-verified"
  | "tier-4-evm-audited";

/**
 * Verification status codes.
 * From VRL Spec §12
 */
export type VerificationStatus =
  | "VALID"
  | "VALID_PARTIAL"
  | "SCHEMA_INVALID"
  | "BUNDLE_ID_MISMATCH"
  | "INTEGRITY_MISMATCH"
  | "CIRCUIT_HASH_MISMATCH"
  | "PROOF_INVALID"
  | "TEE_ATTESTATION_INVALID"
  | "RECOMPUTATION_MISMATCH"
  | "HASH_BINDING_INVALID"
  | "AI_ID_INVALID"
  | "DATA_COMMITMENT_INVALID"
  | "TIMESTAMP_INVALID"
  | "GRAPH_EDGE_INVALID"
  | "UNSUPPORTED_VERSION";

/**
 * AI Identity claim with model information.
 * From VRL Spec §2.2 and §3.3
 */
export interface AIIdentity {
  ai_id: string; // 64-char lowercase hex SHA-256
  provider_id: string; // e.g., "com.openai"
  model_name: string; // e.g., "gpt-4"
  model_version: string; // semantic version
  model_weights_hash: string; // 64-char lowercase hex
  runtime_hash: string; // 64-char lowercase hex
  config_hash: string; // 64-char lowercase hex
  provider_signature?: string; // Ed25519 signature, optional
}

/**
 * Computation record with hashed artefacts.
 * From VRL Spec §3.5
 */
export interface Computation {
  circuit_id: string; // registry identifier
  circuit_version: string; // semantic version
  circuit_hash: string; // 64-char lowercase hex
  input_hash: string; // 64-char lowercase hex
  output_hash: string; // 64-char lowercase hex
  trace_hash: string; // 64-char lowercase hex
  integrity_hash: string; // 64-char lowercase hex
}

/**
 * Cryptographic proof or attestation.
 * From VRL Spec §3.7
 */
export interface Proof {
  proof_system: ProofSystem;
  proof_bytes: string; // hex-encoded proof bytes
  public_inputs: string[]; // hex-encoded field elements
  verification_key_id: string; // 64-char lowercase hex
  proof_hash: string; // 64-char lowercase hex
  commitments?: string[]; // optional Pedersen commitments
}

/**
 * Data commitment binding computation to dataset version.
 * From VRL Spec §6.2
 */
export interface DataCommitment {
  dataset_id: string; // registry identifier
  dataset_version: string; // semantic version
  dataset_hash: string; // 64-char lowercase hex
  provider_id: string; // canonical provider ID
  committed_at: string; // RFC 3339 timestamp
  commitment_hash: string; // 64-char lowercase hex
  provider_signature?: string; // optional Ed25519 signature
}

/**
 * RFC 3161 timestamp authority block.
 * From VRL Spec §8.5
 */
export interface TimestampAuthority {
  tsa_token: string; // base64-encoded RFC 3161 token
  tsa_provider: string; // e.g., "rfc3161.mktime.com"
  tsa_hash_algorithm: string; // e.g., "sha256"
}

/**
 * Blockchain anchor for timestamp proofing.
 * From VRL Spec §8.6
 */
export interface ImmutableAnchor {
  chain: string; // e.g., "ethereum", "solana"
  tx_hash: string; // transaction hash
  block_number: number;
  anchored_at: string; // RFC 3339 timestamp
}

/**
 * Legal metadata and compliance claims.
 * From VRL Spec §8
 */
export interface Legal {
  jurisdictions?: string[]; // list of jurisdiction codes
  admissibility_standard?: string; // e.g., "us-federal", "eidas"
  compliance_flags?: string[]; // e.g., "sec-rule-10b5", "hipaa"
  timestamp_authority?: TimestampAuthority;
  immutable_anchor?: ImmutableAnchor;
}

/**
 * Directed acyclic proof graph for causal dependencies.
 * From VRL Spec §7
 */
export interface ProofGraph {
  depends_on?: string[]; // list of parent bundle IDs
  produced_by?: string; // producer bundle ID
  causal_depth?: number; // depth in dependency DAG
  graph_root_hash?: string; // 64-char lowercase hex
  privacy_tier?: string; // e.g., "private", "public"
}

/**
 * Trust score and anomaly data at issuance.
 * From VRL Spec §9
 */
export interface TrustContext {
  prover_id?: string; // identifier of prover service
  prover_version?: string; // semantic version
  trust_score_at_issuance?: number; // 0.0-1.0
  circuit_certification_tier?: CertificationTier;
  anomaly_flags?: string[]; // suspicious activity indicators
}

/**
 * Complete VRL Proof Bundle.
 * From VRL Spec §3
 *
 * A portable, self-contained artifact that cryptographically attests to
 * the identity, inputs, outputs, and execution correctness of any AI system
 * or deterministic computation.
 */
export interface ProofBundle {
  vrl_version: string; // must be "1.0"
  bundle_id: string; // UUIDv5 from integrity_hash
  issued_at: string; // RFC 3339 timestamp
  ai_identity: AIIdentity;
  computation: Computation;
  proof: Proof;
  data_commitments?: DataCommitment[];
  legal?: Legal;
  proof_graph?: ProofGraph;
  trust_context?: TrustContext;
}

/**
 * Hash computation parameters for AI-ID.
 */
export interface AIIdParams {
  modelWeightsHash: string;
  runtimeHash: string;
  configHash: string;
  providerId: string;
  modelName: string;
  modelVersion: string;
}

/**
 * Hash computation parameters for proof hash.
 */
export interface ProofHashParams {
  circuitHash: string;
  proofBytes: string;
  publicInputs: string[];
  proofSystem: ProofSystem;
  traceHash: string;
}

/**
 * Verification step details.
 */
export interface VerificationStep {
  step: number;
  name: string;
  passed: boolean;
  detail?: string;
}

/**
 * Complete verification result.
 */
export interface VerificationResult {
  status: VerificationStatus;
  errorCodes: string[];
  steps: VerificationStep[];
}
