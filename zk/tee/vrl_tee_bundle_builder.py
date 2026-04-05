"""VRL TEE Proof Bundle Builder.

Builds complete VRL proof bundles for TEE-attested AI inferences.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from utils.canonical import canonical_json
from utils.hashing import sha256_hex
from zk.tee.attestation import TEEAttestation, TEEAttestationPipeline, TEEMode


def build_tee_proof_bundle(
    model_id: str,
    model_version: str,
    provider_id: str,
    input_text: str,
    output_text: str,
    circuit_id: str = 'general/tee-inference-attestation@1.0.0',
    jurisdictions: list[str] | None = None,
    pipeline: TEEAttestationPipeline | None = None,
) -> dict[str, object]:
    """
    End-to-end: run TEE attestation and build a complete VRL proof bundle dict.

    This function:
    1. Computes hashes for model, input, and output
    2. Generates a TEE attestation (in simulation mode by default)
    3. Computes an ai_id hash from model and runtime information
    4. Constructs a full VRL proof bundle with all required fields

    Args:
        model_id: Identifier for the AI model (e.g., 'llama-3-70b-instruct')
        model_version: Version of the model (e.g., '3.0.0')
        provider_id: Provider identifier (e.g., 'meta')
        input_text: The input to the model
        output_text: The output from the model
        circuit_id: Circuit identifier (default: 'general/tee-inference-attestation@1.0.0')
        jurisdictions: Optional list of applicable jurisdictions
        pipeline: Optional TEEAttestationPipeline instance (defaults to SIMULATION mode)

    Returns:
        A complete VRL proof bundle dictionary matching the VRL spec schema.

    Example:
        bundle = build_tee_proof_bundle(
            model_id="llama-3-70b-instruct",
            model_version="3.0.0",
            provider_id="meta",
            input_text="What is the standard dosage of amoxicillin?",
            output_text="The standard adult dose is 250-500mg every 8 hours.",
        )
    """
    if pipeline is None:
        pipeline = TEEAttestationPipeline(mode=TEEMode.SIMULATION)

    # Compute model hash
    model_metadata = {
        'model_id': model_id,
        'model_version': model_version,
        'provider_id': provider_id,
    }
    model_hash = sha256_hex(canonical_json(model_metadata))

    # Run TEE attestation
    attestation = pipeline.attest(
        model_id=model_id,
        model_hash=model_hash,
        input_text=input_text,
        output_text=output_text,
    )

    # Compute ai_id from model and runtime information
    ai_id_payload = {
        'model_id': model_id,
        'model_version': model_version,
        'provider_id': provider_id,
        'runtime_hash': attestation.runtime_hash,
    }
    ai_id = sha256_hex(canonical_json(ai_id_payload))

    # Build integrity hash from all proof components
    integrity_components = {
        'model_hash': attestation.model_hash,
        'input_hash': attestation.input_hash,
        'output_hash': attestation.output_hash,
        'runtime_hash': attestation.runtime_hash,
        'attestation_report_hash': attestation.attestation_report_hash,
    }
    integrity_hash = sha256_hex(canonical_json(integrity_components))

    # Generate timestamps
    now = datetime.now(timezone.utc).isoformat()

    # Build the proof section
    proof_section = pipeline.to_vrl_proof(attestation)

    # Build public inputs for the proof
    public_inputs = {
        'ai_id': ai_id,
        'model_id': model_id,
        'model_version': model_version,
        'provider_id': provider_id,
        'input_hash': attestation.input_hash,
        'output_hash': attestation.output_hash,
        'tee_mode': attestation.tee_mode.value,
    }

    # Build metadata
    metadata = {
        'circuit_id': circuit_id,
        'proof_system': proof_section.get('proof_system', 'sha256-deterministic'),
        'backend': 'tee-attestation-pipeline',
        'model_id': model_id,
        'model_version': model_version,
        'provider_id': provider_id,
        'tee_mode': attestation.tee_mode.value,
    }

    # Build complete VRL proof bundle
    bundle_id = str(uuid.uuid4())

    bundle: dict[str, object] = {
        'version': '1.0.0',
        'bundle_id': bundle_id,
        'proof': {
            'proof_system': proof_section.get('proof_system', 'sha256-deterministic'),
            'tee_mode': attestation.tee_mode.value,
            'model_hash': attestation.model_hash,
            'input_hash': attestation.input_hash,
            'output_hash': attestation.output_hash,
            'runtime_hash': attestation.runtime_hash,
            'attestation_report_bytes': attestation.attestation_report_bytes,
            'attestation_report_hash': attestation.attestation_report_hash,
            'is_simulation': attestation.is_simulation,
        },
        'public_inputs': public_inputs,
        'metadata': metadata,
        'integrity_hash': integrity_hash,
        'created_at': now,
    }

    if attestation.simulation_warning:
        bundle['simulation_warning'] = attestation.simulation_warning

    if jurisdictions:
        bundle['jurisdictions'] = jurisdictions

    return bundle
