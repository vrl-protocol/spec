"""
Verification module for VRL Proof Bundles.

Implements the 10-step verification procedure specified in VRL Spec §12.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid

from .bundle import ProofBundle
from .hashing import (
    sha256, canonical_json,
    compute_integrity_hash, compute_proof_hash, compute_commitment_hash
)


class VerificationStatus(str, Enum):
    """Verification result status codes."""

    VALID = "VALID"
    VALID_PARTIAL = "VALID_PARTIAL"
    SCHEMA_INVALID = "SCHEMA_INVALID"
    BUNDLE_ID_MISMATCH = "BUNDLE_ID_MISMATCH"
    INTEGRITY_MISMATCH = "INTEGRITY_MISMATCH"
    CIRCUIT_HASH_MISMATCH = "CIRCUIT_HASH_MISMATCH"
    PROOF_INVALID = "PROOF_INVALID"
    TEE_ATTESTATION_INVALID = "TEE_ATTESTATION_INVALID"
    RECOMPUTATION_MISMATCH = "RECOMPUTATION_MISMATCH"
    HASH_BINDING_INVALID = "HASH_BINDING_INVALID"
    AI_ID_INVALID = "AI_ID_INVALID"
    DATA_COMMITMENT_INVALID = "DATA_COMMITMENT_INVALID"
    TIMESTAMP_INVALID = "TIMESTAMP_INVALID"
    GRAPH_EDGE_INVALID = "GRAPH_EDGE_INVALID"
    UNSUPPORTED_VERSION = "UNSUPPORTED_VERSION"


@dataclass
class VerificationDetail:
    """Details about a specific verification step."""

    step: str
    status: str  # "PASS" or "FAIL"
    message: str
    error_code: Optional[VerificationStatus] = None


@dataclass
class VerificationResult:
    """
    Complete result of bundle verification.

    Attributes:
        status: Overall verification status
        bundle_id: The bundle being verified
        details: Field-level details for each verification step
        errors: List of error codes encountered
        is_valid: True if status is VALID or VALID_PARTIAL
    """

    status: VerificationStatus
    bundle_id: str
    details: List[VerificationDetail] = field(default_factory=list)
    errors: List[VerificationStatus] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Check if bundle passed verification (VALID or VALID_PARTIAL)."""
        return self.status in (VerificationStatus.VALID, VerificationStatus.VALID_PARTIAL)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            "status": self.status.value,
            "bundle_id": self.bundle_id,
            "is_valid": self.is_valid,
            "errors": [e.value for e in self.errors],
            "details": [
                {
                    "step": d.step,
                    "status": d.status,
                    "message": d.message,
                    "error_code": d.error_code.value if d.error_code else None
                }
                for d in self.details
            ]
        }


class CircuitRegistry:
    """Mock circuit registry for demo purposes."""

    def resolve_circuit(self, circuit_id: str, circuit_version: str) -> Optional[Dict[str, str]]:
        """
        Resolve a circuit from the registry.

        In production, this would query a real circuit registry.
        This mock implementation allows all circuits and uses a deterministic hash.

        Args:
            circuit_id: Circuit identifier (e.g. "trade/import-landed-cost@2.0.0")
            circuit_version: Circuit semantic version

        Returns:
            Dictionary with circuit metadata or None if not found
        """
        # Mock: all circuits resolve with a generic hash
        # In production, this would verify against an actual registry
        circuit_data = {
            "circuit_id": circuit_id,
            "circuit_version": circuit_version,
            "circuit_hash": self._compute_mock_circuit_hash(circuit_id, circuit_version)
        }
        return circuit_data

    def _compute_mock_circuit_hash(self, circuit_id: str, circuit_version: str) -> str:
        """
        Compute a deterministic mock circuit hash.

        In production, this would be retrieved from the registry.
        """
        circuit_obj = {
            "circuit_id": circuit_id,
            "circuit_version": circuit_version,
            "spec_version": "vrl/circuit/1.0"
        }
        canonical = canonical_json(circuit_obj)
        return sha256(canonical)


class Verifier:
    """
    VRL Proof Bundle verifier implementing the 10-step verification procedure.

    Implements the verification procedure from VRL Spec §12.
    """

    VRL_NAMESPACE_UUID = "d9ec1f3e-2d27-45d4-af5f-d8d5efcb7c1e"

    def __init__(self, circuit_registry: Optional[CircuitRegistry] = None):
        """
        Initialize verifier with optional circuit registry.

        Args:
            circuit_registry: CircuitRegistry instance. If None, uses mock registry.
        """
        self.registry = circuit_registry or CircuitRegistry()

    def verify(self, bundle: ProofBundle) -> VerificationResult:
        """
        Verify a proof bundle according to VRL Spec §12 (10-step procedure).

        Args:
            bundle: ProofBundle to verify

        Returns:
            VerificationResult with status and detailed results

        Steps:
            1. Version Check
            2. Schema Validation
            3. bundle_id Recomputation
            4. Integrity Hash Recomputation
            5. Circuit Resolution
            6. Proof Verification
            7. AI-ID Verification
            8. Data Commitment Verification
            9. Timestamp Verification
            10. Proof Graph Edges
        """
        result = VerificationResult(
            status=VerificationStatus.VALID,
            bundle_id=bundle.bundle_id
        )

        # Step 1: Version Check
        if not self._step1_version_check(bundle, result):
            return result

        # Step 2: Schema Validation
        if not self._step2_schema_validation(bundle, result):
            return result

        # Step 3: bundle_id Recomputation
        if not self._step3_bundle_id_check(bundle, result):
            return result

        # Step 4: Integrity Hash Recomputation
        if not self._step4_integrity_hash_check(bundle, result):
            return result

        # Step 5: Circuit Resolution
        if not self._step5_circuit_resolution(bundle, result):
            return result

        # Step 6: Proof Verification
        # Note: Full ZK/TEE verification would require external crypto libraries
        # This implementation validates proof structure
        if not self._step6_proof_structure_validation(bundle, result):
            return result

        # Step 7: AI-ID Verification (if provider_signature present)
        if not self._step7_ai_id_verification(bundle, result):
            return result

        # Step 8: Data Commitment Verification
        if not self._step8_data_commitment_verification(bundle, result):
            return result

        # Step 9: Timestamp Verification (optional, may require network)
        # Only perform if timestamp authority is present
        if bundle.legal and bundle.legal.timestamp_authority:
            if not self._step9_timestamp_verification(bundle, result):
                result.status = VerificationStatus.VALID_PARTIAL
                # Continue; don't fail on optional timestamp

        # Step 10: Proof Graph Edges (optional, may require network)
        if bundle.proof_graph and bundle.proof_graph.depends_on:
            if not self._step10_proof_graph_verification(bundle, result):
                result.status = VerificationStatus.VALID_PARTIAL
                # Continue; don't fail on optional graph verification

        return result

    def _step1_version_check(self, bundle: ProofBundle, result: VerificationResult) -> bool:
        """Step 1: Check vrl_version == "1.0"."""
        if bundle.vrl_version != "1.0":
            detail = VerificationDetail(
                step="Version Check",
                status="FAIL",
                message=f"Unsupported vrl_version: {bundle.vrl_version}",
                error_code=VerificationStatus.UNSUPPORTED_VERSION
            )
            result.details.append(detail)
            result.errors.append(VerificationStatus.UNSUPPORTED_VERSION)
            result.status = VerificationStatus.UNSUPPORTED_VERSION
            return False

        detail = VerificationDetail(
            step="Version Check",
            status="PASS",
            message=f"vrl_version {bundle.vrl_version} is supported"
        )
        result.details.append(detail)
        return True

    def _step2_schema_validation(self, bundle: ProofBundle, result: VerificationResult) -> bool:
        """Step 2: Validate against JSON Schema (§17)."""
        # Check required fields exist
        required_checks = [
            ("bundle_id", bundle.bundle_id, str),
            ("issued_at", bundle.issued_at, str),
            ("ai_identity", bundle.ai_identity, object),
            ("computation", bundle.computation, object),
            ("proof", bundle.proof, object),
        ]

        for field_name, value, expected_type in required_checks:
            if value is None:
                detail = VerificationDetail(
                    step="Schema Validation",
                    status="FAIL",
                    message=f"Required field missing: {field_name}",
                    error_code=VerificationStatus.SCHEMA_INVALID
                )
                result.details.append(detail)
                result.errors.append(VerificationStatus.SCHEMA_INVALID)
                result.status = VerificationStatus.SCHEMA_INVALID
                return False

        # Validate ai_id format (64 hex characters)
        ai_id = bundle.ai_identity.ai_id
        if not self._is_valid_hex_hash(ai_id):
            detail = VerificationDetail(
                step="Schema Validation",
                status="FAIL",
                message=f"Invalid ai_id format: {ai_id}",
                error_code=VerificationStatus.SCHEMA_INVALID
            )
            result.details.append(detail)
            result.errors.append(VerificationStatus.SCHEMA_INVALID)
            result.status = VerificationStatus.SCHEMA_INVALID
            return False

        # Validate hash fields (all should be 64 hex characters)
        hash_fields = [
            ("circuit_hash", bundle.computation.circuit_hash),
            ("input_hash", bundle.computation.input_hash),
            ("output_hash", bundle.computation.output_hash),
            ("trace_hash", bundle.computation.trace_hash),
            ("integrity_hash", bundle.computation.integrity_hash),
            ("proof_hash", bundle.proof.proof_hash),
        ]

        for field_name, hash_value in hash_fields:
            if not self._is_valid_hex_hash(hash_value):
                detail = VerificationDetail(
                    step="Schema Validation",
                    status="FAIL",
                    message=f"Invalid {field_name} format: {hash_value}",
                    error_code=VerificationStatus.SCHEMA_INVALID
                )
                result.details.append(detail)
                result.errors.append(VerificationStatus.SCHEMA_INVALID)
                result.status = VerificationStatus.SCHEMA_INVALID
                return False

        detail = VerificationDetail(
            step="Schema Validation",
            status="PASS",
            message="All required fields present and valid"
        )
        result.details.append(detail)
        return True

    def _step3_bundle_id_check(self, bundle: ProofBundle, result: VerificationResult) -> bool:
        """Step 3: Recompute and verify bundle_id."""
        # UUIDv5(VRL_NAMESPACE, integrity_hash)
        namespace_uuid = uuid.UUID(self.VRL_NAMESPACE_UUID)
        recomputed_uuid = uuid.uuid5(namespace_uuid, bundle.computation.integrity_hash)
        recomputed_bundle_id = str(recomputed_uuid)

        if recomputed_bundle_id != bundle.bundle_id:
            detail = VerificationDetail(
                step="bundle_id Recomputation",
                status="FAIL",
                message=f"bundle_id mismatch: expected {recomputed_bundle_id}, got {bundle.bundle_id}",
                error_code=VerificationStatus.BUNDLE_ID_MISMATCH
            )
            result.details.append(detail)
            result.errors.append(VerificationStatus.BUNDLE_ID_MISMATCH)
            result.status = VerificationStatus.BUNDLE_ID_MISMATCH
            return False

        detail = VerificationDetail(
            step="bundle_id Recomputation",
            status="PASS",
            message=f"bundle_id {bundle.bundle_id} is valid"
        )
        result.details.append(detail)
        return True

    def _step4_integrity_hash_check(self, bundle: ProofBundle, result: VerificationResult) -> bool:
        """Step 4: Recompute integrity_hash."""
        recomputed_integrity = compute_integrity_hash(
            bundle.computation.input_hash,
            bundle.computation.output_hash,
            bundle.computation.trace_hash
        )

        if recomputed_integrity != bundle.computation.integrity_hash:
            detail = VerificationDetail(
                step="Integrity Hash Recomputation",
                status="FAIL",
                message=f"integrity_hash mismatch: expected {recomputed_integrity}, got {bundle.computation.integrity_hash}",
                error_code=VerificationStatus.INTEGRITY_MISMATCH
            )
            result.details.append(detail)
            result.errors.append(VerificationStatus.INTEGRITY_MISMATCH)
            result.status = VerificationStatus.INTEGRITY_MISMATCH
            return False

        detail = VerificationDetail(
            step="Integrity Hash Recomputation",
            status="PASS",
            message=f"integrity_hash {bundle.computation.integrity_hash} is valid"
        )
        result.details.append(detail)
        return True

    def _step5_circuit_resolution(self, bundle: ProofBundle, result: VerificationResult) -> bool:
        """Step 5: Resolve circuit and verify circuit_hash."""
        circuit = self.registry.resolve_circuit(
            bundle.computation.circuit_id,
            bundle.computation.circuit_version
        )

        if circuit is None:
            detail = VerificationDetail(
                step="Circuit Resolution",
                status="FAIL",
                message=f"Circuit not found: {bundle.computation.circuit_id}@{bundle.computation.circuit_version}",
                error_code=VerificationStatus.CIRCUIT_HASH_MISMATCH
            )
            result.details.append(detail)
            result.errors.append(VerificationStatus.CIRCUIT_HASH_MISMATCH)
            result.status = VerificationStatus.CIRCUIT_HASH_MISMATCH
            return False

        if circuit["circuit_hash"] != bundle.computation.circuit_hash:
            detail = VerificationDetail(
                step="Circuit Resolution",
                status="FAIL",
                message=f"circuit_hash mismatch: expected {circuit['circuit_hash']}, got {bundle.computation.circuit_hash}",
                error_code=VerificationStatus.CIRCUIT_HASH_MISMATCH
            )
            result.details.append(detail)
            result.errors.append(VerificationStatus.CIRCUIT_HASH_MISMATCH)
            result.status = VerificationStatus.CIRCUIT_HASH_MISMATCH
            return False

        detail = VerificationDetail(
            step="Circuit Resolution",
            status="PASS",
            message=f"Circuit {bundle.computation.circuit_id} verified with matching hash"
        )
        result.details.append(detail)
        return True

    def _step6_proof_structure_validation(self, bundle: ProofBundle, result: VerificationResult) -> bool:
        """
        Step 6: Proof structure validation.

        Full ZK/TEE verification requires external crypto libraries.
        This validates proof structure and recomputes proof_hash.
        """
        proof = bundle.proof

        # Validate proof_system
        valid_systems = {
            "plonk-halo2-pasta", "plonk-halo2-bn254",
            "groth16-bn254", "stark", "zk-ml",
            "tee-intel-tdx", "tee-amd-sev-snp", "tee-aws-nitro",
            "sha256-deterministic", "api-hash-binding"
        }
        if proof.proof_system not in valid_systems:
            detail = VerificationDetail(
                step="Proof Structure Validation",
                status="FAIL",
                message=f"Invalid proof_system: {proof.proof_system}",
                error_code=VerificationStatus.PROOF_INVALID
            )
            result.details.append(detail)
            result.errors.append(VerificationStatus.PROOF_INVALID)
            result.status = VerificationStatus.PROOF_INVALID
            return False

        # Recompute proof_hash
        recomputed_proof_hash = compute_proof_hash(
            bundle.computation.circuit_hash,
            proof.proof_bytes,
            proof.public_inputs,
            proof.proof_system,
            bundle.computation.trace_hash
        )

        if recomputed_proof_hash != proof.proof_hash:
            detail = VerificationDetail(
                step="Proof Structure Validation",
                status="FAIL",
                message=f"proof_hash mismatch: expected {recomputed_proof_hash}, got {proof.proof_hash}",
                error_code=VerificationStatus.PROOF_INVALID
            )
            result.details.append(detail)
            result.errors.append(VerificationStatus.PROOF_INVALID)
            result.status = VerificationStatus.PROOF_INVALID
            return False

        detail = VerificationDetail(
            step="Proof Structure Validation",
            status="PASS",
            message=f"Proof structure valid for {proof.proof_system}"
        )
        result.details.append(detail)
        return True

    def _step7_ai_id_verification(self, bundle: ProofBundle, result: VerificationResult) -> bool:
        """
        Step 7: AI-ID verification (if provider_signature present).

        This step verifies the AI-ID recomputation. Provider signature verification
        would require access to the provider's public key and Ed25519 verification.
        """
        # If no provider signature, skip full verification but note it
        if not bundle.ai_identity.provider_signature:
            detail = VerificationDetail(
                step="AI-ID Verification",
                status="PASS",
                message="No provider_signature; AI-ID is advisory only"
            )
            result.details.append(detail)
            return True

        # In production, would verify provider_signature against provider's public key
        # For now, just validate the AI-ID format
        ai_id = bundle.ai_identity.ai_id
        if not self._is_valid_hex_hash(ai_id):
            detail = VerificationDetail(
                step="AI-ID Verification",
                status="FAIL",
                message=f"Invalid ai_id format: {ai_id}",
                error_code=VerificationStatus.AI_ID_INVALID
            )
            result.details.append(detail)
            result.errors.append(VerificationStatus.AI_ID_INVALID)
            result.status = VerificationStatus.AI_ID_INVALID
            return False

        detail = VerificationDetail(
            step="AI-ID Verification",
            status="PASS",
            message=f"AI-ID {ai_id} is valid (provider_signature present but not verified)"
        )
        result.details.append(detail)
        return True

    def _step8_data_commitment_verification(self, bundle: ProofBundle, result: VerificationResult) -> bool:
        """Step 8: Data commitment verification."""
        if not bundle.data_commitments:
            detail = VerificationDetail(
                step="Data Commitment Verification",
                status="PASS",
                message="No data commitments"
            )
            result.details.append(detail)
            return True

        for i, commitment in enumerate(bundle.data_commitments):
            # Recompute commitment_hash
            recomputed_hash = compute_commitment_hash(
                commitment.dataset_id,
                commitment.dataset_version,
                commitment.dataset_hash,
                commitment.provider_id,
                commitment.committed_at
            )

            if recomputed_hash != commitment.commitment_hash:
                detail = VerificationDetail(
                    step=f"Data Commitment Verification [{i}]",
                    status="FAIL",
                    message=f"commitment_hash mismatch for {commitment.dataset_id}",
                    error_code=VerificationStatus.DATA_COMMITMENT_INVALID
                )
                result.details.append(detail)
                result.errors.append(VerificationStatus.DATA_COMMITMENT_INVALID)
                result.status = VerificationStatus.DATA_COMMITMENT_INVALID
                return False

        detail = VerificationDetail(
            step="Data Commitment Verification",
            status="PASS",
            message=f"All {len(bundle.data_commitments)} data commitments verified"
        )
        result.details.append(detail)
        return True

    def _step9_timestamp_verification(self, bundle: ProofBundle, result: VerificationResult) -> bool:
        """
        Step 9: Timestamp authority verification.

        Full RFC 3161 verification requires TSA certificate chain validation.
        This validates the structure only.
        """
        if not bundle.legal or not bundle.legal.timestamp_authority:
            return True

        tsa = bundle.legal.timestamp_authority
        if not tsa.tsa_token or not tsa.tsa_provider or not tsa.tsa_hash_algorithm:
            detail = VerificationDetail(
                step="Timestamp Verification",
                status="FAIL",
                message="Incomplete timestamp_authority block",
                error_code=VerificationStatus.TIMESTAMP_INVALID
            )
            result.details.append(detail)
            result.errors.append(VerificationStatus.TIMESTAMP_INVALID)
            return False

        detail = VerificationDetail(
            step="Timestamp Verification",
            status="PASS",
            message=f"Timestamp token from {tsa.tsa_provider} (RFC 3161 verification skipped)"
        )
        result.details.append(detail)
        return True

    def _step10_proof_graph_verification(self, bundle: ProofBundle, result: VerificationResult) -> bool:
        """
        Step 10: Proof graph edge verification.

        In production, this would recursively fetch and verify referenced bundles.
        This validates the structure only.
        """
        if not bundle.proof_graph or not bundle.proof_graph.depends_on:
            return True

        for bundle_id in bundle.proof_graph.depends_on:
            # In production, would fetch bundle by ID and verify it
            # For now, just validate UUID format
            try:
                uuid.UUID(bundle_id)
            except ValueError:
                detail = VerificationDetail(
                    step="Proof Graph Verification",
                    status="FAIL",
                    message=f"Invalid bundle_id in depends_on: {bundle_id}",
                    error_code=VerificationStatus.GRAPH_EDGE_INVALID
                )
                result.details.append(detail)
                result.errors.append(VerificationStatus.GRAPH_EDGE_INVALID)
                return False

        detail = VerificationDetail(
            step="Proof Graph Verification",
            status="PASS",
            message=f"Proof graph edges valid (recursive verification skipped)"
        )
        result.details.append(detail)
        return True

    @staticmethod
    def _is_valid_hex_hash(value: str) -> bool:
        """Check if value is a valid 64-character lowercase hex string."""
        if not isinstance(value, str):
            return False
        if len(value) != 64:
            return False
        try:
            int(value, 16)
            return value == value.lower()
        except ValueError:
            return False
