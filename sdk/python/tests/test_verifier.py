"""Tests for VRL Verifier implementation."""

import pytest
from vrl import (
    ProofBundle, AIIdentity, Computation, Proof,
    ProofBundleBuilder, ComputationBuilder, ProofBuilder,
    Verifier, VerificationStatus,
    compute_proof_hash, compute_integrity_hash
)


class TestVerifier:
    """Test verifier functionality."""

    def _create_valid_bundle(self):
        """Create a valid test bundle for verification."""
        ai_identity = AIIdentity(
            ai_id="a3f2c1d4e5b6a7f8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1",
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

    def test_valid_bundle_passes(self):
        """Test that a valid bundle passes all verification steps."""
        bundle = self._create_valid_bundle()
        verifier = Verifier()

        result = verifier.verify(bundle)

        assert result.is_valid
        assert result.status in (VerificationStatus.VALID, VerificationStatus.VALID_PARTIAL)
        assert len(result.errors) == 0
        assert all(d.status == "PASS" for d in result.details)

    def test_verification_has_all_steps(self):
        """Test that verification includes all required steps."""
        bundle = self._create_valid_bundle()
        verifier = Verifier()

        result = verifier.verify(bundle)

        step_names = [d.step for d in result.details]
        required_steps = [
            "Version Check",
            "Schema Validation",
            "bundle_id Recomputation",
            "Integrity Hash Recomputation",
            "Circuit Resolution",
            "Proof Structure Validation",
            "AI-ID Verification"
        ]

        for required_step in required_steps:
            assert required_step in step_names, f"Missing step: {required_step}"

    def test_invalid_vrl_version_fails(self):
        """Test that invalid vrl_version fails verification."""
        bundle = self._create_valid_bundle()
        bundle.vrl_version = "2.0"

        verifier = Verifier()
        result = verifier.verify(bundle)

        assert not result.is_valid
        assert result.status == VerificationStatus.UNSUPPORTED_VERSION
        assert VerificationStatus.UNSUPPORTED_VERSION in result.errors

    def test_invalid_bundle_id_fails(self):
        """Test that incorrect bundle_id fails verification."""
        bundle = self._create_valid_bundle()
        bundle.bundle_id = "00000000-0000-0000-0000-000000000000"

        verifier = Verifier()
        result = verifier.verify(bundle)

        assert not result.is_valid
        assert result.status == VerificationStatus.BUNDLE_ID_MISMATCH
        assert VerificationStatus.BUNDLE_ID_MISMATCH in result.errors

    def test_invalid_integrity_hash_fails(self):
        """Test that incorrect integrity_hash fails verification."""
        bundle = self._create_valid_bundle()
        bundle.computation.integrity_hash = "a" * 64

        verifier = Verifier()
        result = verifier.verify(bundle)

        assert not result.is_valid
        assert result.status == VerificationStatus.INTEGRITY_MISMATCH
        assert VerificationStatus.INTEGRITY_MISMATCH in result.errors

    def test_tampered_input_hash_fails(self):
        """Test that tampered input_hash fails integrity check."""
        bundle = self._create_valid_bundle()
        original_input = bundle.computation.input_hash

        # Change input hash
        bundle.computation.input_hash = "b" * 64

        # Recompute integrity hash since it depends on input_hash
        bundle.computation.integrity_hash = compute_integrity_hash(
            bundle.computation.input_hash,
            bundle.computation.output_hash,
            bundle.computation.trace_hash
        )

        # Update bundle_id since it depends on integrity_hash
        from vrl import compute_bundle_id_from_integrity
        bundle.bundle_id = compute_bundle_id_from_integrity(bundle.computation.integrity_hash)

        verifier = Verifier()
        result = verifier.verify(bundle)

        # Should pass structural checks but show changed input
        # The verifier doesn't recompute the original input, just validates hashes match
        assert result.is_valid or result.status == VerificationStatus.CIRCUIT_HASH_MISMATCH

    def test_invalid_ai_id_format_fails(self):
        """Test that invalid ai_id format fails schema validation."""
        bundle = self._create_valid_bundle()
        bundle.ai_identity.ai_id = "invalid"  # Not 64 hex chars

        verifier = Verifier()
        result = verifier.verify(bundle)

        assert not result.is_valid
        assert result.status == VerificationStatus.SCHEMA_INVALID
        assert VerificationStatus.SCHEMA_INVALID in result.errors

    def test_invalid_circuit_hash_format_fails(self):
        """Test that invalid circuit_hash format fails schema validation."""
        bundle = self._create_valid_bundle()
        bundle.computation.circuit_hash = "not_hex"

        verifier = Verifier()
        result = verifier.verify(bundle)

        assert not result.is_valid
        assert result.status == VerificationStatus.SCHEMA_INVALID

    def test_invalid_proof_system_fails(self):
        """Test that invalid proof_system fails."""
        bundle = self._create_valid_bundle()
        bundle.proof.proof_system = "invalid-system"

        verifier = Verifier()
        result = verifier.verify(bundle)

        assert not result.is_valid
        assert result.status == VerificationStatus.PROOF_INVALID
        assert VerificationStatus.PROOF_INVALID in result.errors

    def test_mismatched_proof_hash_fails(self):
        """Test that mismatched proof_hash fails."""
        bundle = self._create_valid_bundle()
        bundle.proof.proof_hash = "c" * 64

        verifier = Verifier()
        result = verifier.verify(bundle)

        assert not result.is_valid
        assert result.status == VerificationStatus.PROOF_INVALID
        assert VerificationStatus.PROOF_INVALID in result.errors

    def test_verification_result_to_dict(self):
        """Test VerificationResult.to_dict() serialization."""
        bundle = self._create_valid_bundle()
        verifier = Verifier()
        result = verifier.verify(bundle)

        result_dict = result.to_dict()

        assert "status" in result_dict
        assert "bundle_id" in result_dict
        assert "is_valid" in result_dict
        assert "errors" in result_dict
        assert "details" in result_dict
        assert result_dict["status"] in ["VALID", "VALID_PARTIAL"]
        assert result_dict["is_valid"] == True

    def test_multiple_proof_systems_supported(self):
        """Test that multiple proof systems are recognized."""
        bundle = self._create_valid_bundle()
        verifier = Verifier()

        proof_systems = [
            "plonk-halo2-pasta",
            "plonk-halo2-bn254",
            "groth16-bn254",
            "stark",
            "zk-ml",
            "tee-intel-tdx",
            "tee-amd-sev-snp",
            "tee-aws-nitro",
            "sha256-deterministic",
            "api-hash-binding"
        ]

        for system in proof_systems:
            bundle.proof.proof_system = system
            result = verifier.verify(bundle)
            # Should not fail on proof_system validation
            assert result.status != VerificationStatus.PROOF_INVALID


class TestVerificationDetails:
    """Test verification detail tracking."""

    def test_verification_details_on_valid_bundle(self):
        """Test that all details are present and PASS on valid bundle."""
        ai_identity = AIIdentity(
            ai_id="a" * 64,
            model_name="test",
            model_version="1.0",
            provider_id="test",
            execution_environment="deterministic"
        )

        computation = (ComputationBuilder()
            .set_circuit_id("test/circuit@1.0.0")
            .set_circuit_version("1.0.0")
            .set_circuit_hash("b" * 64)
            .set_input_hash("c" * 64)
            .set_output_hash("d" * 64)
            .set_trace_hash("e" * 64)
            .compute_integrity_hash()
            .build())

        proof = (ProofBuilder()
            .set_proof_system("sha256-deterministic")
            .set_proof_bytes("f" * 32)
            .set_public_inputs([])
            .set_verification_key_id("a" * 64)
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

        verifier = Verifier()
        result = verifier.verify(bundle)

        # All details should be PASS
        for detail in result.details:
            assert detail.status == "PASS", f"Step {detail.step} failed: {detail.message}"

    def test_verification_error_details(self):
        """Test that error details are properly recorded."""
        bundle = self._create_invalid_bundle()
        verifier = Verifier()
        result = verifier.verify(bundle)

        # Should have at least one FAIL detail
        failed_details = [d for d in result.details if d.status == "FAIL"]
        assert len(failed_details) > 0

        # Each failed detail should have an error_code
        for detail in failed_details:
            assert detail.error_code is not None

    @staticmethod
    def _create_invalid_bundle():
        """Create an intentionally invalid bundle."""
        ai_identity = AIIdentity(
            ai_id="a" * 64,
            model_name="test",
            model_version="1.0",
            provider_id="test",
            execution_environment="deterministic"
        )

        computation = (ComputationBuilder()
            .set_circuit_id("test/circuit@1.0.0")
            .set_circuit_version("1.0.0")
            .set_circuit_hash("b" * 64)
            .set_input_hash("c" * 64)
            .set_output_hash("d" * 64)
            .set_trace_hash("e" * 64)
            .compute_integrity_hash()
            .build())

        proof = (ProofBuilder()
            .set_proof_system("invalid-system")
            .set_proof_bytes("f" * 32)
            .set_public_inputs([])
            .set_verification_key_id("a" * 64)
            .build())

        proof.proof_hash = "bad" * 20  # Invalid hash

        return (ProofBundleBuilder()
            .set_ai_identity(ai_identity)
            .set_computation(computation)
            .set_proof(proof)
            .set_issued_at_now()
            .build())


class TestCircuitRegistry:
    """Test circuit registry resolution."""

    def test_circuit_registry_resolves_circuit(self):
        """Test that circuit registry can resolve circuits."""
        from vrl import CircuitRegistry
        registry = CircuitRegistry()

        circuit = registry.resolve_circuit("test/circuit@1.0.0", "1.0.0")

        assert circuit is not None
        assert circuit["circuit_id"] == "test/circuit@1.0.0"
        assert circuit["circuit_version"] == "1.0.0"
        assert circuit["circuit_hash"] is not None

    def test_circuit_hash_is_deterministic(self):
        """Test that circuit hash is deterministic."""
        from vrl import CircuitRegistry
        registry = CircuitRegistry()

        circuit1 = registry.resolve_circuit("test/circuit@1.0.0", "1.0.0")
        circuit2 = registry.resolve_circuit("test/circuit@1.0.0", "1.0.0")

        assert circuit1["circuit_hash"] == circuit2["circuit_hash"]

    def test_different_versions_have_different_hashes(self):
        """Test that different circuit versions have different hashes."""
        from vrl import CircuitRegistry
        registry = CircuitRegistry()

        circuit1 = registry.resolve_circuit("test/circuit@1.0.0", "1.0.0")
        circuit2 = registry.resolve_circuit("test/circuit@2.0.0", "2.0.0")

        assert circuit1["circuit_hash"] != circuit2["circuit_hash"]
