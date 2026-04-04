"""
Hash utilities for VRL Proof Bundle computation.

Implements all hash functions defined in VRL Spec §11 using SHA-256 with canonical JSON.
"""

import hashlib
import json
from typing import Any, Dict, List


def canonical_json(obj: Any) -> str:
    """
    Serialize an object to canonical JSON as specified in VRL Spec §10.

    Rules:
    - Object keys sorted lexicographically (Unicode code point order)
    - No whitespace outside strings
    - Strings as UTF-8, lowercase unicode escapes
    - Numerics used in hashing as strings
    - Booleans and null as-is
    - Array order preserved

    Args:
        obj: Object to serialize (dict, list, string, number, bool, or None)

    Returns:
        Canonical JSON string (no whitespace)
    """
    if isinstance(obj, dict):
        # Sort keys lexicographically
        sorted_items = sorted(obj.items())
        pairs = []
        for k, v in sorted_items:
            # Keys are always strings, quoted
            key_json = json.dumps(k, separators=(',', ':'), ensure_ascii=True)
            val_json = canonical_json(v)
            pairs.append(f'{key_json}:{val_json}')
        return '{' + ','.join(pairs) + '}'
    elif isinstance(obj, list):
        items = [canonical_json(item) for item in obj]
        return '[' + ','.join(items) + ']'
    elif isinstance(obj, str):
        return json.dumps(obj, separators=(',', ':'), ensure_ascii=True)
    elif isinstance(obj, bool):
        return 'true' if obj else 'false'
    elif obj is None:
        return 'null'
    elif isinstance(obj, (int, float)):
        # For hashing, numbers should be represented as strings in the JSON
        # But when passed to canonical_json directly, serialize as JSON number
        return json.dumps(obj, separators=(',', ':'))
    else:
        return json.dumps(obj, separators=(',', ':'), ensure_ascii=True)


def sha256(data: str) -> str:
    """
    Compute SHA-256 hash of a string and return as lowercase hex.

    Args:
        data: String to hash (will be encoded as UTF-8)

    Returns:
        Lowercase hex-encoded SHA-256 digest (64 characters)
    """
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def compute_ai_id(
    model_weights_hash: str,
    runtime_hash: str,
    config_hash: str,
    provider_id: str,
    model_name: str,
    model_version: str
) -> str:
    """
    Compute AI-ID as specified in VRL Spec §2.2.

    AI_ID = SHA-256(canonical_json({
        "model_weights_hash": ...,
        "runtime_hash": ...,
        "config_hash": ...,
        "provider_id": ...,
        "model_name": ...,
        "model_version": ...,
        "spec_version": "vrl/ai-id/1.0"
    }))

    Args:
        model_weights_hash: SHA-256 of model weights
        runtime_hash: SHA-256 of runtime environment descriptor
        config_hash: SHA-256 of inference config
        provider_id: Provider canonical name (e.g. "com.openai")
        model_name: Model name
        model_version: Semantic version

    Returns:
        Lowercase hex-encoded AI-ID (64 characters)
    """
    ai_id_object = {
        "model_weights_hash": model_weights_hash,
        "runtime_hash": runtime_hash,
        "config_hash": config_hash,
        "provider_id": provider_id,
        "model_name": model_name,
        "model_version": model_version,
        "spec_version": "vrl/ai-id/1.0"
    }
    canonical = canonical_json(ai_id_object)
    return sha256(canonical)


def compute_integrity_hash(
    input_hash: str,
    output_hash: str,
    trace_hash: str
) -> str:
    """
    Compute integrity_hash as specified in VRL Spec §11.4.

    integrity_hash = SHA-256(input_hash + output_hash + trace_hash)

    where + is string concatenation (no separator).

    Args:
        input_hash: SHA-256 of inputs
        output_hash: SHA-256 of outputs
        trace_hash: SHA-256 of trace steps

    Returns:
        Lowercase hex-encoded integrity hash (64 characters)
    """
    concatenated = input_hash + output_hash + trace_hash
    return sha256(concatenated)


def compute_proof_hash(
    circuit_hash: str,
    proof_bytes: str,
    public_inputs: List[str],
    proof_system: str,
    trace_hash: str
) -> str:
    """
    Compute proof_hash as specified in VRL Spec §11.5.

    proof_hash = SHA-256(canonical_json({
        "circuit_hash": ...,
        "proof_bytes": ...,
        "public_inputs": [...],
        "proof_system": ...,
        "trace_hash": ...,
        "public_inputs_hash": ...
    }))

    Args:
        circuit_hash: SHA-256 of circuit constraints
        proof_bytes: Hex-encoded proof bytes
        public_inputs: Array of hex-encoded field elements
        proof_system: Proof system identifier
        trace_hash: SHA-256 of trace steps

    Returns:
        Lowercase hex-encoded proof hash (64 characters)
    """
    # Compute public_inputs_hash as SHA-256 of canonical_json(public_inputs)
    public_inputs_hash = sha256(canonical_json(public_inputs))

    proof_hash_object = {
        "circuit_hash": circuit_hash,
        "proof_bytes": proof_bytes,
        "proof_system": proof_system,
        "public_inputs": public_inputs,
        "public_inputs_hash": public_inputs_hash,
        "trace_hash": trace_hash
    }
    canonical = canonical_json(proof_hash_object)
    return sha256(canonical)


def compute_input_hash(inputs_object: Dict[str, Any]) -> str:
    """
    Compute input_hash as specified in VRL Spec §11.1.

    input_hash = SHA-256(canonical_json(inputs_object))

    All numeric values should be represented as strings in the object.

    Args:
        inputs_object: Dictionary of inputs (should have string-valued numerics)

    Returns:
        Lowercase hex-encoded input hash (64 characters)
    """
    canonical = canonical_json(inputs_object)
    return sha256(canonical)


def compute_output_hash(outputs_object: Dict[str, Any]) -> str:
    """
    Compute output_hash as specified in VRL Spec §11.2.

    output_hash = SHA-256(canonical_json(outputs_object))

    All numeric values should be represented as strings in the object.

    Args:
        outputs_object: Dictionary of outputs (should have string-valued numerics)

    Returns:
        Lowercase hex-encoded output hash (64 characters)
    """
    canonical = canonical_json(outputs_object)
    return sha256(canonical)


def compute_trace_hash(trace_steps: List[Dict[str, Any]]) -> str:
    """
    Compute trace_hash as specified in VRL Spec §11.3.

    trace_hash = SHA-256(canonical_json(trace_steps_array))

    Each step should have: step, rule_ref, inputs, outputs with string-valued numerics.

    Args:
        trace_steps: Ordered array of trace step objects

    Returns:
        Lowercase hex-encoded trace hash (64 characters)
    """
    canonical = canonical_json(trace_steps)
    return sha256(canonical)


def compute_commitment_hash(
    dataset_id: str,
    dataset_version: str,
    dataset_hash: str,
    provider_id: str,
    committed_at: str
) -> str:
    """
    Compute commitment_hash for data commitments as specified in VRL Spec §6.2.

    commitment_hash = SHA-256(canonical_json({
        "committed_at": ...,
        "dataset_hash": ...,
        "dataset_id": ...,
        "dataset_version": ...,
        "provider_id": ...
    }))

    Args:
        dataset_id: Registry identifier for the dataset
        dataset_version: Version of the dataset
        dataset_hash: SHA-256 of dataset content
        provider_id: Canonical ID of dataset provider
        committed_at: RFC 3339 timestamp of commitment

    Returns:
        Lowercase hex-encoded commitment hash (64 characters)
    """
    commitment_object = {
        "committed_at": committed_at,
        "dataset_hash": dataset_hash,
        "dataset_id": dataset_id,
        "dataset_version": dataset_version,
        "provider_id": provider_id
    }
    canonical = canonical_json(commitment_object)
    return sha256(canonical)


def compute_bundle_id_from_integrity(integrity_hash: str) -> str:
    """
    Compute bundle_id as UUIDv5 from integrity_hash.

    bundle_id = UUIDv5(VRL_NAMESPACE_UUID, integrity_hash)

    Args:
        integrity_hash: The integrity hash of the bundle

    Returns:
        UUIDv5 string as bundle_id
    """
    import uuid
    VRL_NAMESPACE_UUID = "d9ec1f3e-2d27-45d4-af5f-d8d5efcb7c1e"
    namespace_uuid = uuid.UUID(VRL_NAMESPACE_UUID)
    bundle_uuid = uuid.uuid5(namespace_uuid, integrity_hash)
    return str(bundle_uuid)
