"""Tests for TEE attestation pipeline and VRL bundle builder."""
from __future__ import annotations

from zk.tee.attestation import TEEAttestation, TEEAttestationPipeline, TEEMode
from zk.tee.vrl_tee_bundle_builder import build_tee_proof_bundle


def test_simulation_attestation() -> None:
    """Test that simulation mode produces valid attestations with all required fields."""
    pipeline = TEEAttestationPipeline(mode=TEEMode.SIMULATION)
    attestation = pipeline.attest(
        model_id='test-model-v1',
        model_hash='abc123def456' * 5 + '1234',  # 64 chars
        input_text='Test input',
        output_text='Test output',
    )

    # Verify all required fields are present
    assert attestation.tee_mode == TEEMode.SIMULATION
    assert attestation.model_hash == 'abc123def456' * 5 + '1234'
    assert isinstance(attestation.input_hash, str)
    assert len(attestation.input_hash) == 64
    assert isinstance(attestation.output_hash, str)
    assert len(attestation.output_hash) == 64
    assert isinstance(attestation.runtime_hash, str)
    assert len(attestation.runtime_hash) == 64
    assert isinstance(attestation.attestation_report_bytes, str)
    assert len(attestation.attestation_report_bytes) == 64
    assert isinstance(attestation.attestation_report_hash, str)
    assert len(attestation.attestation_report_hash) == 64
    assert attestation.is_simulation is True
    assert attestation.simulation_warning == 'SIMULATION MODE: not hardware-attested'


def test_tee_bundle_is_deterministic() -> None:
    """Test that same inputs produce same integrity_hash (deterministic)."""
    model_id = 'gpt-4-turbo'
    model_version = '2024-04'
    provider_id = 'openai'
    input_text = 'What is AI?'
    output_text = 'Artificial Intelligence is...'

    bundle1 = build_tee_proof_bundle(
        model_id=model_id,
        model_version=model_version,
        provider_id=provider_id,
        input_text=input_text,
        output_text=output_text,
    )

    bundle2 = build_tee_proof_bundle(
        model_id=model_id,
        model_version=model_version,
        provider_id=provider_id,
        input_text=input_text,
        output_text=output_text,
    )

    # bundle_id should be different (UUIDs)
    assert bundle1['bundle_id'] != bundle2['bundle_id']

    # integrity_hash should be the same
    assert bundle1['integrity_hash'] == bundle2['integrity_hash']

    # Model hash and hashes should be the same
    assert bundle1['proof']['model_hash'] == bundle2['proof']['model_hash']
    assert bundle1['proof']['input_hash'] == bundle2['proof']['input_hash']
    assert bundle1['proof']['output_hash'] == bundle2['proof']['output_hash']


def test_to_vrl_proof_structure() -> None:
    """Test that to_vrl_proof produces the correct VRL proof structure."""
    pipeline = TEEAttestationPipeline(mode=TEEMode.SIMULATION)
    attestation = pipeline.attest(
        model_id='model-x',
        model_hash='0123456789abcdef' * 4,
        input_text='input data',
        output_text='output data',
    )

    vrl_proof = pipeline.to_vrl_proof(attestation)

    # Verify required fields
    assert 'proof_system' in vrl_proof
    assert vrl_proof['proof_system'] == 'sha256-deterministic'
    assert 'tee_mode' in vrl_proof
    assert vrl_proof['tee_mode'] == 'simulation'
    assert 'model_hash' in vrl_proof
    assert 'input_hash' in vrl_proof
    assert 'output_hash' in vrl_proof
    assert 'runtime_hash' in vrl_proof
    assert 'attestation_report_bytes' in vrl_proof
    assert 'attestation_report_hash' in vrl_proof
    assert 'is_simulation' in vrl_proof
    assert vrl_proof['is_simulation'] is True
    assert 'simulation_warning' in vrl_proof


def test_build_tee_proof_bundle_full_schema() -> None:
    """Test that build_tee_proof_bundle produces a complete, valid bundle."""
    model_id = 'llama-3-70b-instruct'
    model_version = '3.0.0'
    provider_id = 'meta'
    input_text = 'What is the standard dosage of amoxicillin?'
    output_text = 'The standard adult dose is 250-500mg every 8 hours.'

    bundle = build_tee_proof_bundle(
        model_id=model_id,
        model_version=model_version,
        provider_id=provider_id,
        input_text=input_text,
        output_text=output_text,
    )

    # Verify top-level structure
    assert 'version' in bundle
    assert bundle['version'] == '1.0.0'
    assert 'bundle_id' in bundle
    assert isinstance(bundle['bundle_id'], str)
    assert len(bundle['bundle_id']) > 0

    # Verify proof section
    assert 'proof' in bundle
    proof = bundle['proof']
    assert 'proof_system' in proof
    assert 'tee_mode' in proof
    assert 'model_hash' in proof
    assert 'input_hash' in proof
    assert 'output_hash' in proof
    assert 'runtime_hash' in proof
    assert 'attestation_report_bytes' in proof
    assert 'attestation_report_hash' in proof
    assert 'is_simulation' in proof

    # Verify public_inputs section
    assert 'public_inputs' in bundle
    public_inputs = bundle['public_inputs']
    assert 'ai_id' in public_inputs
    assert 'model_id' in public_inputs
    assert public_inputs['model_id'] == model_id
    assert 'model_version' in public_inputs
    assert public_inputs['model_version'] == model_version
    assert 'provider_id' in public_inputs
    assert public_inputs['provider_id'] == provider_id
    assert 'input_hash' in public_inputs
    assert 'output_hash' in public_inputs
    assert 'tee_mode' in public_inputs

    # Verify metadata section
    assert 'metadata' in bundle
    metadata = bundle['metadata']
    assert 'circuit_id' in metadata
    assert 'proof_system' in metadata
    assert 'backend' in metadata
    assert metadata['backend'] == 'tee-attestation-pipeline'

    # Verify integrity_hash and timestamps
    assert 'integrity_hash' in bundle
    assert isinstance(bundle['integrity_hash'], str)
    assert len(bundle['integrity_hash']) == 64
    assert 'created_at' in bundle
    assert isinstance(bundle['created_at'], str)

    # Verify simulation warning is present
    assert 'simulation_warning' in bundle
    assert bundle['simulation_warning'] == 'SIMULATION MODE: not hardware-attested'


def test_build_tee_proof_bundle_with_jurisdictions() -> None:
    """Test that jurisdictions are included in the bundle when provided."""
    bundle = build_tee_proof_bundle(
        model_id='test-model',
        model_version='1.0.0',
        provider_id='test-provider',
        input_text='test input',
        output_text='test output',
        jurisdictions=['US', 'EU', 'APAC'],
    )

    assert 'jurisdictions' in bundle
    assert bundle['jurisdictions'] == ['US', 'EU', 'APAC']


def test_build_tee_proof_bundle_custom_circuit_id() -> None:
    """Test that custom circuit_id is included in metadata."""
    custom_circuit_id = 'medical/pharmaceutical-dosage-checker@2.1.5'
    bundle = build_tee_proof_bundle(
        model_id='test-model',
        model_version='1.0.0',
        provider_id='test-provider',
        input_text='test input',
        output_text='test output',
        circuit_id=custom_circuit_id,
    )

    assert 'metadata' in bundle
    assert bundle['metadata']['circuit_id'] == custom_circuit_id


def test_intel_tdx_not_implemented() -> None:
    """Test that Intel TDX mode raises NotImplementedError outside enclave."""
    pipeline = TEEAttestationPipeline(mode=TEEMode.INTEL_TDX)

    try:
        pipeline.attest(
            model_id='test-model',
            model_hash='0123456789abcdef' * 4,
            input_text='test input',
            output_text='test output',
        )
        assert False, 'Should have raised NotImplementedError'
    except NotImplementedError as e:
        assert 'Intel TDX attestation is only available' in str(e)
        assert 'TDX enclave' in str(e)


def test_amd_sev_snp_not_implemented() -> None:
    """Test that AMD SEV-SNP mode raises NotImplementedError outside enclave."""
    pipeline = TEEAttestationPipeline(mode=TEEMode.AMD_SEV_SNP)

    try:
        pipeline.attest(
            model_id='test-model',
            model_hash='0123456789abcdef' * 4,
            input_text='test input',
            output_text='test output',
        )
        assert False, 'Should have raised NotImplementedError'
    except NotImplementedError as e:
        assert 'AMD SEV-SNP attestation is only available' in str(e)
        assert 'SEV-SNP enclave' in str(e)
