"""Tests for VRL ProofBundle creation, serialization, and round-trip JSON."""

import pytest
import json
from vrl import (
    ProofBundle, AIIdentity, Computation, Proof, DataCommitment,
    ProofBundleBuilder, ComputationBuilder, ProofBuilder,
    compute_proof_hash, compute_commitment_hash
)


class TestBundleCreation:
    """Test basic bundle creation and structure."""

    def test_create_bundle_with_builders(self):
        """Test creating a complete bundle with builder APIs."""
        ai_identity = AIIdentity(
            ai_id="a" * 64,
            model_name="gpt-4-turbo",
            model_version="2024-04-09",
            provider_id="com.openai",
            execution_environment="api-attested"
        )

        computation = (ComputationBuilder()
            .set_circuit_id("trade/import-landed-cost@2.0.0")
            .set_circuit_version("2.0.0")
            .set_circuit_hash("3fa24c7763608b01b4c7e411655ebc75ff7a906c38bd79a4cc3be0f4479cdf23")
            .set_input_hash("ebf1f0aa67d10b8472fd7f1af22fc9370ecb813243f928b4f5528ab27457fea7")
            .set_output_hash("0c866369e1ab87b0d0b624c0fdeb490aa05fa2524e9368a023308a1437ec5b5b")
            .set_trace_hash("e14d0cb8d4a11cf1db1def3942fa7246b72cb6989463e8d379ade6e90a0405e6")
            .compute_integrity_hash()
            .build())

        proof = (ProofBuilder()
            .set_proof_system("sha256-deterministic")
            .set_proof_bytes("0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d")
            .set_public_inputs([])
            .set_verification_key_id("aadfa62983a64cb674b1b9b1c4379d8a01e02948fed731506de4bcf2950012a0")
            .set_proof_hash("0" * 64)
            .build())

        proof.proof_hash = compute_proof_hash(
            computation.circuit_hash,
            proof.proof_bytes,
            proof.public_inputs,
            proof.proof_system,
            computation.trace_hash
        )

        bundle = (ProofBundleBuilder()
            .set_ai_identity(ai_identity)
            .set_computation(computation)
            .set_proof(proof)
            .set_issued_at_now()
            .build())

        assert bundle.vrl_version == "1.0"
        assert bundle.bundle_id is not None
        assert bundle.issued_at is not None
        assert bundle.ai_identity.model_name == "gpt-4-turbo"
        assert bundle.computation.circuit_id == "trade/import-landed-cost@2.0.0"
        assert bundle.proof.proof_system == "sha256-deterministic"

    def test_bundle_requires_ai_identity(self):
        """Test that bundle requires ai_identity."""
        computation = (ComputationBuilder()
            .set_circuit_id("test/circuit@1.0.0")
            .set_circuit_version("1.0.0")
            .set_circuit_hash("a" * 64)
            .set_input_hash("b" * 64)
            .set_output_hash("c" * 64)
            .set_trace_hash("d" * 64)
            .compute_integrity_hash()
            .build())

        proof = (ProofBuilder()
            .set_proof_system("sha256-deterministic")
            .set_proof_bytes("e" * 32)
            .set_public_inputs([])
            .set_verification_key_id("f" * 64)
            .set_proof_hash("0" * 64)
            .build())
        proof.proof_hash = compute_proof_hash(
            computation.circuit_hash, proof.proof_bytes,
            proof.public_inputs, proof.proof_system, computation.trace_hash
        )

        builder = (ProofBundleBuilder()
            .set_computation(computation)
            .set_proof(proof)
            .set_issued_at_now())

        with pytest.raises(ValueError, match="ai_identity is required"):
            builder.build()

    def test_bundle_requires_computation(self):
        """Test that bundle requires computation."""
        ai_identity = AIIdentity(
            ai_id="a" * 64,
            model_name="test-model",
            model_version="1.0.0",
            provider_id="test",
            execution_environment="deterministic"
        )

        proof = (ProofBuilder()
            .set_proof_system("sha256-deterministic")
            .set_proof_bytes("b" * 32)
            .set_public_inputs([])
            .set_verification_key_id("c" * 64)
            .set_proof_hash("d" * 64)
            .build())

        builder = (ProofBundleBuilder()
            .set_ai_identity(ai_identity)
            .set_proof(proof)
            .set_issued_at_now())

        with pytest.raises(ValueError, match="computation is required"):
            builder.build()

    def test_bundle_requires_proof(self):
        """Test that bundle requires proof."""
        ai_identity = AIIdentity(
            ai_id="a" * 64,
            model_name="test-model",
            model_version="1.0.0",
            provider_id="test",
            execution_environment="deterministic"
        )

        computation = (ComputationBuilder()
            .set_circuit_id("test/circuit@1.0.0")
            .set_circuit_version("1.0.0")
            .set_circuit_hash("a" * 64)
            .set_input_hash("b" * 64)
            .set_output_hash("c" * 64)
            .set_trace_hash("d" * 64)
            .compute_integrity_hash()
            .build())

        builder = (ProofBundleBuilder()
            .set_ai_identity(ai_identity)
            .set_computation(computation)
            .set_issued_at_now())

        with pytest.raises(ValueError, match="proof is required"):
            builder.build()


class TestBundleSerialization:
    """Test JSON serialization and deserialization."""

    def _create_test_bundle(self):
        """Create a test bundle for serialization tests."""
        ai_identity = AIIdentity(
            ai_id="a" * 64,
            model_name="gpt-4-turbo",
            model_version="2024-04-09",
            provider_id="com.openai",
            execution_environment="api-attested"
        )

        computation = (ComputationBuilder()
            .set_circuit_id("trade/import-landed-cost@2.0.0")
            .set_circuit_version("2.0.0")
            .set_circuit_hash("3fa24c7763608b01b4c7e411655ebc75ff7a906c38bd79a4cc3be0f4479cdf23")
            .set_input_hash("ebf1f0aa67d10b8472fd7f1af22fc9370ecb813243f928b4f5528ab27457fea7")
            .set_output_hash("0c866369e1ab87b0d0b624c0fdeb490aa05fa2524e9368a023308a1437ec5b5b")
            .set_trace_hash("e14d0cb8d4a11cf1db1def3942fa7246b72cb6989463e8d379ade6e90a0405e6")
            .compute_integrity_hash()
            .build())

        proof = (ProofBuilder()
            .set_proof_system("sha256-deterministic")
            .set_proof_bytes("0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d")
            .set_public_inputs([])
            .set_verification_key_id("aadfa62983a64cb674b1b9b1c4379d8a01e02948fed731506de4bcf2950012a0")
            .set_proof_hash("0" * 64)
            .build())

        proof.proof_hash = compute_proof_hash(
            computation.circuit_hash,
            proof.proof_bytes,
            proof.public_inputs,
            proof.proof_system,
            computation.trace_hash
        )

        return (ProofBundleBuilder()
            .set_ai_identity(ai_identity)
            .set_computation(computation)
            .set_proof(proof)
            .set_issued_at("2026-04-04T12:00:00.000Z")
            .build())

    def test_bundle_to_dict(self):
        """Test bundle to_dict serialization."""
        bundle = self._create_test_bundle()
        bundle_dict = bundle.to_dict()

        assert bundle_dict["vrl_version"] == "1.0"
        assert bundle_dict["bundle_id"] == bundle.bundle_id
        assert bundle_dict["issued_at"] == "2026-04-04T12:00:00.000Z"
        assert "ai_identity" in bundle_dict
        assert "computation" in bundle_dict
        assert "proof" in bundle_dict
        assert bundle_dict["ai_identity"]["model_name"] == "gpt-4-turbo"

    def test_bundle_to_json_compact(self):
        """Test bundle to JSON with compact format."""
        bundle = self._create_test_bundle()
        json_str = bundle.to_json(pretty=False)

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["vrl_version"] == "1.0"
        # Compact format should not have extra whitespace
        assert "\n" not in json_str

    def test_bundle_to_json_pretty(self):
        """Test bundle to JSON with pretty format."""
        bundle = self._create_test_bundle()
        json_str = bundle.to_json(pretty=True)

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["vrl_version"] == "1.0"
        # Pretty format should have indentation
        assert "\n" in json_str

    def test_bundle_from_dict(self):
        """Test creating bundle from dictionary."""
        bundle = self._create_test_bundle()
        bundle_dict = bundle.to_dict()

        # Recreate from dict
        bundle2 = ProofBundle.from_dict(bundle_dict)

        assert bundle2.vrl_version == bundle.vrl_version
        assert bundle2.bundle_id == bundle.bundle_id
        assert bundle2.issued_at == bundle.issued_at
        assert bundle2.ai_identity.model_name == bundle.ai_identity.model_name
        assert bundle2.computation.circuit_id == bundle.computation.circuit_id
        assert bundle2.proof.proof_system == bundle.proof.proof_system

    def test_bundle_from_json(self):
        """Test creating bundle from JSON string."""
        bundle = self._create_test_bundle()
        json_str = bundle.to_json(pretty=True)

        # Recreate from JSON
        bundle2 = ProofBundle.from_json(json_str)

        assert bundle2.vrl_version == bundle.vrl_version
        assert bundle2.bundle_id == bundle.bundle_id
        assert bundle2.ai_identity.model_name == bundle.ai_identity.model_name

    def test_bundle_round_trip_json(self):
        """Test round-trip: bundle -> JSON -> bundle."""
        bundle1 = self._create_test_bundle()
        json_str = bundle1.to_json(pretty=False)
        bundle2 = ProofBundle.from_json(json_str)
        json_str2 = bundle2.to_json(pretty=False)

        # Both JSON representations should be identical
        assert json_str == json_str2

    def test_bundle_with_data_commitments(self):
        """Test bundle serialization with data commitments."""
        bundle = self._create_test_bundle()

        commitment = DataCommitment(
            dataset_id="cbp/hts-tariff-rules",
            dataset_version="2026.1.0",
            dataset_hash="d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5",
            provider_id="gov.us.cbp",
            committed_at="2026-04-01T00:00:00.000Z",
            commitment_hash=compute_commitment_hash(
                "cbp/hts-tariff-rules",
                "2026.1.0",
                "d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5",
                "gov.us.cbp",
                "2026-04-01T00:00:00.000Z"
            )
        )

        bundle2 = (ProofBundleBuilder()
            .set_ai_identity(bundle.ai_identity)
            .set_computation(bundle.computation)
            .set_proof(bundle.proof)
            .set_issued_at(bundle.issued_at)
            .add_data_commitment(commitment)
            .set_bundle_id(bundle.bundle_id)
            .build())

        bundle_dict = bundle2.to_dict()
        assert "data_commitments" in bundle_dict
        assert len(bundle_dict["data_commitments"]) == 1
        assert bundle_dict["data_commitments"][0]["dataset_id"] == "cbp/hts-tariff-rules"

        # Round-trip
        bundle3 = ProofBundle.from_dict(bundle_dict)
        assert bundle3.data_commitments is not None
        assert len(bundle3.data_commitments) == 1
        assert bundle3.data_commitments[0].dataset_id == "cbp/hts-tariff-rules"


class TestBundleValidation:
    """Test bundle validation and error handling."""

    def test_invalid_vrl_version(self):
        """Test that invalid vrl_version raises error."""
        data = {
            "vrl_version": "2.0",  # Invalid
            "bundle_id": "00000000-0000-0000-0000-000000000000",
            "issued_at": "2026-04-04T12:00:00.000Z",
            "ai_identity": {
                "ai_id": "a" * 64,
                "model_name": "test",
                "model_version": "1.0",
                "provider_id": "test",
                "execution_environment": "deterministic"
            },
            "computation": {
                "circuit_id": "test/circuit@1.0",
                "circuit_version": "1.0",
                "circuit_hash": "b" * 64,
                "input_hash": "c" * 64,
                "output_hash": "d" * 64,
                "trace_hash": "e" * 64,
                "integrity_hash": "f" * 64
            },
            "proof": {
                "proof_system": "sha256-deterministic",
                "proof_bytes": "a" * 32,
                "public_inputs": [],
                "verification_key_id": "b" * 64,
                "proof_hash": "c" * 64
            }
        }

        with pytest.raises(ValueError, match="Unsupported vrl_version"):
            ProofBundle.from_dict(data)

    def test_missing_required_field(self):
        """Test that missing required field raises error."""
        data = {
            "vrl_version": "1.0",
            # Missing bundle_id
            "issued_at": "2026-04-04T12:00:00.000Z",
            "ai_identity": {
                "ai_id": "a" * 64,
                "model_name": "test",
                "model_version": "1.0",
                "provider_id": "test",
                "execution_environment": "deterministic"
            },
            "computation": {
                "circuit_id": "test/circuit@1.0",
                "circuit_version": "1.0",
                "circuit_hash": "b" * 64,
                "input_hash": "c" * 64,
                "output_hash": "d" * 64,
                "trace_hash": "e" * 64,
                "integrity_hash": "f" * 64
            },
            "proof": {
                "proof_system": "sha256-deterministic",
                "proof_bytes": "a" * 32,
                "public_inputs": [],
                "verification_key_id": "b" * 64,
                "proof_hash": "c" * 64
            }
        }

        with pytest.raises(ValueError, match="Missing required"):
            ProofBundle.from_dict(data)

    def test_invalid_json(self):
        """Test that invalid JSON raises error."""
        with pytest.raises(ValueError, match="Invalid JSON"):
            ProofBundle.from_json("not valid json {")
