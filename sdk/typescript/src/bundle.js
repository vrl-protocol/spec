/**
 * Bundle serialization and deserialization utilities.
 */

const { canonicalJson } = require("./hashing");

/**
 * Parse a ProofBundle from JSON string.
 *
 * @param {string} json JSON string representation of a bundle
 * @returns {object} Parsed ProofBundle
 * @throws {Error} if JSON is invalid or doesn't conform to schema
 */
function parseBundle(json) {
  let data;
  try {
    data = JSON.parse(json);
  } catch (e) {
    throw new Error(`Invalid JSON: ${e.message}`);
  }

  if (typeof data !== "object" || data === null) {
    throw new Error("Root must be an object");
  }

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
    if (!(field in data)) {
      throw new Error(`Missing required field: ${field}`);
    }
  }

  if (data.vrl_version !== "1.0") {
    throw new Error(`Unsupported vrl_version: ${data.vrl_version}`);
  }

  // Basic type validation
  if (typeof data.bundle_id !== "string") {
    throw new Error("bundle_id must be a string");
  }
  if (typeof data.issued_at !== "string") {
    throw new Error("issued_at must be a string");
  }

  return data;
}

/**
 * Serialize a ProofBundle to JSON string.
 *
 * Uses canonical JSON format (sorted keys, no whitespace).
 *
 * @param {object} bundle ProofBundle to serialize
 * @returns {string} JSON string representation
 */
function serializeBundle(bundle) {
  return canonicalJson(bundle);
}

module.exports = {
  parseBundle,
  serializeBundle,
};
