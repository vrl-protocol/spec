/**
 * Hash utilities for VRL Proof Bundle computation.
 * Implements all hash functions defined in VRL Spec §11 using SHA-256 with canonical JSON.
 */

import { createHash } from "crypto";
import { AIIdParams, ProofHashParams } from "./types";

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
 * @param obj Object to serialize (dict, list, string, number, bool, or null)
 * @returns Canonical JSON string (no whitespace)
 */
export function canonicalJson(obj: unknown): string {
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
    const dict = obj as Record<string, unknown>;
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
 * @param input String to hash (will be encoded as UTF-8)
 * @returns Lowercase hex-encoded SHA-256 digest (64 characters)
 */
export function sha256(input: string | Buffer): string {
  const hash = createHash("sha256");
  hash.update(input);
  return hash.digest("hex");
}

/**
 * Compute integrity_hash as specified in VRL Spec §11.4.
 *
 * integrity_hash = SHA-256(input_hash + output_hash + trace_hash)
 *
 * where + is string concatenation (no separator).
 *
 * @param inputHash SHA-256 of inputs
 * @param outputHash SHA-256 of outputs
 * @param traceHash SHA-256 of trace steps
 * @returns Lowercase hex-encoded integrity hash (64 characters)
 */
export function computeIntegrityHash(
  inputHash: string,
  outputHash: string,
  traceHash: string
): string {
  const concatenated = inputHash + outputHash + traceHash;
  return sha256(concatenated);
}

/**
 * Compute AI-ID as specified in VRL Spec §2.2.
 *
 * AI_ID = SHA-256(canonical_json({
 *   "model_weights_hash": ...,
 *   "runtime_hash": ...,
 *   "config_hash": ...,
 *   "provider_id": ...,
 *   "model_name": ...,
 *   "model_version": ...,
 *   "spec_version": "vrl/ai-id/1.0"
 * }))
 *
 * @param params Parameters for AI-ID computation
 * @returns Lowercase hex-encoded AI-ID (64 characters)
 */
export function computeAIId(params: AIIdParams): string {
  const aiIdObject: Record<string, string> = {
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
 * proof_hash = SHA-256(canonical_json({
 *   "circuit_hash": ...,
 *   "proof_bytes": ...,
 *   "public_inputs": [...],
 *   "proof_system": ...,
 *   "trace_hash": ...,
 *   "public_inputs_hash": ...
 * }))
 *
 * @param params Parameters for proof hash computation
 * @returns Lowercase hex-encoded proof hash (64 characters)
 */
export function computeProofHash(params: ProofHashParams): string {
  // Compute public_inputs_hash as SHA-256 of canonical_json(public_inputs)
  const publicInputsHash = sha256(canonicalJson(params.publicInputs));

  const proofHashObject: Record<string, unknown> = {
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
 * input_hash = SHA-256(canonical_json(inputs_object))
 *
 * @param inputsObject Dictionary of inputs
 * @returns Lowercase hex-encoded input hash (64 characters)
 */
export function computeInputHash(inputsObject: Record<string, unknown>): string {
  const canonical = canonicalJson(inputsObject);
  return sha256(canonical);
}

/**
 * Compute output_hash as specified in VRL Spec §11.2.
 *
 * output_hash = SHA-256(canonical_json(outputs_object))
 *
 * @param outputsObject Dictionary of outputs
 * @returns Lowercase hex-encoded output hash (64 characters)
 */
export function computeOutputHash(
  outputsObject: Record<string, unknown>
): string {
  const canonical = canonicalJson(outputsObject);
  return sha256(canonical);
}

/**
 * Compute trace_hash as specified in VRL Spec §11.3.
 *
 * trace_hash = SHA-256(canonical_json(trace_steps_array))
 *
 * Each step should have: step, rule_ref, inputs, outputs with string-valued numerics.
 *
 * @param traceSteps Ordered array of trace step objects
 * @returns Lowercase hex-encoded trace hash (64 characters)
 */
export function computeTraceHash(
  traceSteps: Array<Record<string, unknown>>
): string {
  const canonical = canonicalJson(traceSteps);
  return sha256(canonical);
}

/**
 * Compute commitment_hash for data commitments as specified in VRL Spec §6.2.
 *
 * commitment_hash = SHA-256(canonical_json({
 *   "committed_at": ...,
 *   "dataset_hash": ...,
 *   "dataset_id": ...,
 *   "dataset_version": ...,
 *   "provider_id": ...
 * }))
 *
 * @param datasetId Registry identifier for the dataset
 * @param datasetVersion Version of the dataset
 * @param datasetHash SHA-256 of dataset content
 * @param providerId Canonical ID of dataset provider
 * @param committedAt RFC 3339 timestamp of commitment
 * @returns Lowercase hex-encoded commitment hash (64 characters)
 */
export function computeCommitmentHash(
  datasetId: string,
  datasetVersion: string,
  datasetHash: string,
  providerId: string,
  committedAt: string
): string {
  const commitmentObject: Record<string, string> = {
    committed_at: committedAt,
    dataset_hash: datasetHash,
    dataset_id: datasetId,
    dataset_version: datasetVersion,
    provider_id: providerId,
  };

  const canonical = canonicalJson(commitmentObject);
  return sha256(canonical);
}
