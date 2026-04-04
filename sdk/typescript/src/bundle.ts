/**
 * Bundle serialization and deserialization utilities.
 */

import { ProofBundle } from "./types";
import { canonicalJson } from "./hashing";

/**
 * Parse a ProofBundle from JSON string.
 *
 * @param json JSON string representation of a bundle
 * @returns Parsed ProofBundle
 * @throws Error if JSON is invalid or doesn't conform to schema
 */
export function parseBundle(json: string): ProofBundle {
  let data: unknown;
  try {
    data = JSON.parse(json);
  } catch (e) {
    throw new Error(`Invalid JSON: ${e instanceof Error ? e.message : String(e)}`);
  }

  if (typeof data !== "object" || data === null) {
    throw new Error("Root must be an object");
  }

  const bundle = data as Record<string, unknown>;

  // Validate required fields
  const required = [
    "vrl_version",
    "bundle_id",
    "issued_at",
    "ai_identity",
    "computation",
    "proof",
  ];
  for (const field of required) {
    if (!(field in bundle)) {
      throw new Error(`Missing required field: ${field}`);
    }
  }

  if (bundle.vrl_version !== "1.0") {
    throw new Error(`Unsupported vrl_version: ${bundle.vrl_version}`);
  }

  // Basic type validation
  if (typeof bundle.bundle_id !== "string") {
    throw new Error("bundle_id must be a string");
  }
  if (typeof bundle.issued_at !== "string") {
    throw new Error("issued_at must be a string");
  }

  return bundle as ProofBundle;
}

/**
 * Serialize a ProofBundle to JSON string.
 *
 * Uses canonical JSON format (sorted keys, no whitespace).
 *
 * @param bundle ProofBundle to serialize
 * @returns JSON string representation
 */
export function serializeBundle(bundle: ProofBundle): string {
  return canonicalJson(bundle);
}
