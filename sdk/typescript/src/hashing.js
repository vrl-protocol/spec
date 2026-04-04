/**
 * Hash utilities for VRL Proof Bundle computation.
 * Implements all hash functions defined in VRL Spec §11 using SHA-256 with canonical JSON.
 */

const { createHash } = require("crypto");

/**
 * Serialize an object to canonical JSON as specified in VRL Spec §10.
 *
 * Rules:
 * - Object keys sorted lexicographically (Unicode code point order)
 * - No whitespace outside strings
 * - Strings as UTF-8, lowercase unicode escapes
 * - Numerics used in hashing as strings
 * - Booleans and null as-is
 * - Array order preserved
 *
 * @param {any} obj Object to serialize
 * @returns {string} Canonical JSON string (no whitespace)
 */
function canonicalJson(obj) {
  if (obj === null) {
    return "null";
  }

  if (typeof obj === "boolean") {
    return obj ? "true" : "false";
  }

  if (typeof obj === "string") {
    return JSON.stringify(obj);
  }

  if (typeof obj === "number") {
    return JSON.stringify(obj);
  }

  if (Array.isArray(obj)) {
    const items = obj.map((item) => canonicalJson(item));
    return "[" + items.join(",") + "]";
  }

  if (typeof obj === "object") {
    const dict = obj;
    const keys = Object.keys(dict).sort();
    const pairs = keys.map((k) => {
      const keyJson = JSON.stringify(k);
      const valJson = canonicalJson(dict[k]);
      return keyJson + ":" + valJson;
    });
    return "{" + pairs.join(",") + "}";
  }

  throw new Error(`Cannot serialize type: ${typeof obj}`);
}

/**
 * Compute SHA-256 hash of a string and return as lowercase hex.
 *
 * @param {string|Buffer} input String to hash
 * @returns {string} Lowercase hex-encoded SHA-256 digest (64 characters)
 */
function sha256(input) {
  const hash = createHash("sha256");
  hash.update(input);
  return hash.digest("hex");
}

/**
 * Compute integrity_hash as specified in VRL Spec §11.4.
 *
 * @param {string} inputHash SHA-256 of inputs
 * @param {string} outputHash SHA-256 of outputs
 * @param {string} traceHash SHA-256 of trace steps
 * @returns {string} Lowercase hex-encoded integrity hash
 */
function computeIntegrityHash(inputHash, outputHash, traceHash) {
  const concatenated = inputHash + outputHash + traceHash;
  return sha256(concatenated);
}

/**
 * Compute AI-ID as specified in VRL Spec §2.2.
 *
 * @param {object} params Parameters for AI-ID computation
 * @returns {string} Lowercase hex-encoded AI-ID
 */
function computeAIId(params) {
  const aiIdObject = {
    config_hash: params.configHash,
    model_name: params.modelName,
    model_version: params.modelVersion,
    model_weights_hash: params.modelWeightsHash,
    provider_id: params.providerId,
    runtime_hash: params.runtimeHash,
    spec_version: "vrl/ai-id/1.0",
  };

  const canonical = canonicalJson(aiIdObject);
  return sha256(canonical);
}

/**
 * Compute proof_hash as specified in VRL Spec §11.5.
 *
 * @param {object} params Parameters for proof hash computation
 * @returns {string} Lowercase hex-encoded proof hash
 */
function computeProofHash(params) {
  const publicInputsHash = sha256(canonicalJson(params.publicInputs));

  const proofHashObject = {
    circuit_hash: params.circuitHash,
    proof_bytes: params.proofBytes,
    proof_system: params.proofSystem,
    public_inputs: params.publicInputs,
    public_inputs_hash: publicInputsHash,
    trace_hash: params.traceHash,
  };

  const canonical = canonicalJson(proofHashObject);
  return sha256(canonical);
}

/**
 * Compute input_hash as specified in VRL Spec §11.1.
 *
 * @param {object} inputsObject Dictionary of inputs
 * @returns {string} Lowercase hex-encoded input hash
 */
function computeInputHash(inputsObject) {
  const canonical = canonicalJson(inputsObject);
  return sha256(canonical);
}

/**
 * Compute output_hash as specified in VRL Spec §11.2.
 *
 * @param {object} outputsObject Dictionary of outputs
 * @returns {string} Lowercase hex-encoded output hash
 */
function computeOutputHash(outputsObject) {
  const canonical = canonicalJson(outputsObject);
  return sha256(canonical);
}

/**
 * Compute trace_hash as specified in VRL Spec §11.3.
 *
 * @param {Array} traceSteps Ordered array of trace step objects
 * @returns {string} Lowercase hex-encoded trace hash
 */
function computeTraceHash(traceSteps) {
  const canonical = canonicalJson(traceSteps);
  return sha256(canonical);
}

/**
 * Compute commitment_hash for data commitments as specified in VRL Spec §6.2.
 *
 * @param {string} datasetId Registry identifier for the dataset
 * @param {string} datasetVersion Version of the dataset
 * @param {string} datasetHash SHA-256 of dataset content
 * @param {string} providerId Canonical ID of dataset provider
 * @param {string} committedAt RFC 3339 timestamp of commitment
 * @returns {string} Lowercase hex-encoded commitment hash
 */
function computeCommitmentHash(
  datasetId,
  datasetVersion,
  datasetHash,
  providerId,
  committedAt
) {
  const commitmentObject = {
    committed_at: committedAt,
    dataset_hash: datasetHash,
    dataset_id: datasetId,
    dataset_version: datasetVersion,
    provider_id: providerId,
  };

  const canonical = canonicalJson(commitmentObject);
  return sha256(canonical);
}

module.exports = {
  canonicalJson,
  sha256,
  computeIntegrityHash,
  computeAIId,
  computeProofHash,
  computeInputHash,
  computeOutputHash,
  computeTraceHash,
  computeCommitmentHash,
};
