/**
 * VRL TypeScript SDK - Main Export
 */

// Hashing utilities
const {
  canonicalJson,
  sha256,
  computeIntegrityHash,
  computeAIId,
  computeProofHash,
  computeInputHash,
  computeOutputHash,
  computeTraceHash,
  computeCommitmentHash,
} = require("./hashing");

// Bundle utilities
const { parseBundle, serializeBundle } = require("./bundle");

// Builder classes
const {
  ProofBundleBuilder,
  ComputationBuilder,
  ProofBuilder,
} = require("./builder");

// Verifier
const { Verifier } = require("./verifier");

module.exports = {
  // Types (exported for documentation, but JS doesn't enforce them)

  // Hashing utilities
  canonicalJson,
  sha256,
  computeIntegrityHash,
  computeAIId,
  computeProofHash,
  computeInputHash,
  computeOutputHash,
  computeTraceHash,
  computeCommitmentHash,

  // Bundle utilities
  parseBundle,
  serializeBundle,

  // Builder classes
  ProofBundleBuilder,
  ComputationBuilder,
  ProofBuilder,

  // Verifier
  Verifier,
};
