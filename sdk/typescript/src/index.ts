/**
 * VRL TypeScript SDK - Main Export
 */

// Type exports
export {
  ProofSystem,
  CertificationTier,
  VerificationStatus,
  AIIdentity,
  Computation,
  Proof,
  DataCommitment,
  TimestampAuthority,
  ImmutableAnchor,
  Legal,
  ProofGraph,
  TrustContext,
  ProofBundle,
  AIIdParams,
  ProofHashParams,
  VerificationStep,
  VerificationResult,
} from "./types";

// Hashing utilities
export {
  canonicalJson,
  sha256,
  computeIntegrityHash,
  computeAIId,
  computeProofHash,
  computeInputHash,
  computeOutputHash,
  computeTraceHash,
  computeCommitmentHash,
} from "./hashing";

// Bundle utilities
export { parseBundle, serializeBundle } from "./bundle";

// Builder classes
export {
  ProofBundleBuilder,
  ComputationBuilder,
  ProofBuilder,
} from "./builder";

// Verifier
export { Verifier } from "./verifier";
