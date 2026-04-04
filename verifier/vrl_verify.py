#!/usr/bin/env python3
"""
Standalone VRL Proof Bundle Verifier.

Implements the 10-step verification procedure from VRL Spec §12.
No external dependencies — uses only stdlib (json, hashlib, uuid, sys).

Usage:
    python vrl_verify.py <bundle.json> [--verbose] [--json-output]
    cat bundle.json | python vrl_verify.py [--verbose] [--json-output]

Exit codes:
    0 — VALID (or VALID_PARTIAL with optional checks omitted)
    1 — INVALID (failed verification)
    2 — ERROR (invalid input or parsing error)
"""

import sys
import json
import hashlib
import uuid
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict


# ============================================================================
# HASHING UTILITIES (copied inline from SDK to avoid dependencies)
# ============================================================================

def canonical_json(obj: Any) -> str:
    """
    Serialize to canonical JSON per VRL Spec §10.

    - Object keys sorted lexicographically
    - No whitespace outside strings
    - Strings as UTF-8, lowercase unicode escapes
    - Array order preserved
    """
    if isinstance(obj, dict):
        sorted_items = sorted(obj.items())
        pairs = []
        for k, v in sorted_items:
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
        return json.dumps(obj, separators=(',', ':'))
    else:
        return json.dumps(obj, separators=(',', ':'), ensure_ascii=True)


def sha256(data: str) -> str:
    """SHA-256 hash and return as lowercase hex."""
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def compute_integrity_hash(input_hash: str, output_hash: str, trace_hash: str) -> str:
    """Integrity hash = SHA-256(input_hash + output_hash + trace_hash)."""
    concatenated = input_hash + output_hash + trace_hash
    return sha256(concatenated)


def compute_proof_hash(
    circuit_hash: str,
    proof_bytes: str,
    public_inputs: List[str],
    proof_system: str,
    trace_hash: str
) -> str:
    """Proof hash per spec §11.5."""
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


def compute_commitment_hash(
    dataset_id: str,
    dataset_version: str,
    dataset_hash: str,
    provider_id: str,
    committed_at: str
) -> str:
    """Data commitment hash per spec §6.2."""
    commitment_object = {
        "committed_at": committed_at,
        "dataset_hash": dataset_hash,
        "dataset_id": dataset_id,
        "dataset_version": dataset_version,
        "provider_id": provider_id
    }
    canonical = canonical_json(commitment_object)
    return sha256(canonical)


# ============================================================================
# DATA CLASSES & ENUMS
# ============================================================================

class VerificationStatus:
    """Status codes for verification results."""
    VALID = "VALID"
    VALID_PARTIAL = "VALID_PARTIAL"
    SCHEMA_INVALID = "SCHEMA_INVALID"
    BUNDLE_ID_MISMATCH = "BUNDLE_ID_MISMATCH"
    INTEGRITY_MISMATCH = "INTEGRITY_MISMATCH"
    CIRCUIT_HASH_MISMATCH = "CIRCUIT_HASH_MISMATCH"
    PROOF_INVALID = "PROOF_INVALID"
    AI_ID_INVALID = "AI_ID_INVALID"
    DATA_COMMITMENT_INVALID = "DATA_COMMITMENT_INVALID"
    TIMESTAMP_INVALID = "TIMESTAMP_INVALID"
    GRAPH_EDGE_INVALID = "GRAPH_EDGE_INVALID"
    UNSUPPORTED_VERSION = "UNSUPPORTED_VERSION"


@dataclass
class VerificationDetail:
    """Details about a verification step."""
    step: str
    status: str  # "PASS" or "FAIL"
    message: str
    error_code: Optional[str] = None
    computed_value: Optional[str] = None
    expected_value: Optional[str] = None


@dataclass
class VerificationResult:
    """Complete verification result."""
    status: str
    bundle_id: str
    details: List[VerificationDetail]
    errors: List[str]
    is_valid: bool

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "status": self.status,
            "bundle_id": self.bundle_id,
            "is_valid": self.is_valid,
            "errors": self.errors,
            "details": [
                {
                    "step": d.step,
                    "status": d.status,
                    "message": d.message,
                    "error_code": d.error_code,
                    "computed_value": d.computed_value,
                    "expected_value": d.expected_value
                }
                for d in self.details
            ]
        }


# ============================================================================
# CIRCUIT REGISTRY (MOCK)
# ============================================================================

class CircuitRegistry:
    """Mock circuit registry for demo."""

    def resolve_circuit(self, circuit_id: str, circuit_version: str) -> Optional[Dict[str, str]]:
        """Resolve a circuit (mock: accepts all and computes deterministic hash)."""
        circuit_data = {
            "circuit_id": circuit_id,
            "circuit_version": circuit_version,
            "circuit_hash": self._compute_mock_circuit_hash(circuit_id, circuit_version)
        }
        return circuit_data

    @staticmethod
    def _compute_mock_circuit_hash(circuit_id: str, circuit_version: str) -> str:
        """Deterministic mock circuit hash."""
        circuit_obj = {
            "circuit_id": circuit_id,
            "circuit_version": circuit_version,
            "spec_version": "vrl/circuit/1.0"
        }
        canonical = canonical_json(circuit_obj)
        return sha256(canonical)


# ============================================================================
# VERIFIER
# ============================================================================

class Verifier:
    """VRL Proof Bundle verifier implementing 10-step verification (Spec §12)."""

    VRL_NAMESPACE_UUID = "d9ec1f3e-2d27-45d4-af5f-d8d5efcb7c1e"

    def __init__(self, verbose: bool = False, registry: Optional[CircuitRegistry] = None):
        """Initialize verifier."""
        self.verbose = verbose
        self.registry = registry or CircuitRegistry()

    def verify(self, bundle_dict: Dict[str, Any]) -> VerificationResult:
        """
        Verify a proof bundle (dict parsed from JSON).

        Returns VerificationResult with detailed step-by-step results.
        """
        bundle_id = bundle_dict.get("bundle_id", "unknown")
        result = VerificationResult(
            status=VerificationStatus.VALID,
            bundle_id=bundle_id,
            details=[],
            errors=[],
            is_valid=True
        )

        # Step 1: Version Check
        if not self._step1_version_check(bundle_dict, result):
            return result

        # Step 2: Schema Validation
        if not self._step2_schema_validation(bundle_dict, result):
            return result

        # Step 3: bundle_id Recomputation
        if not self._step3_bundle_id_check(bundle_dict, result):
            return result

        # Step 4: Integrity Hash Recomputation
        if not self._step4_integrity_hash_check(bundle_dict, result):
            return result

        # Step 5: Circuit Resolution
        if not self._step5_circuit_resolution(bundle_dict, result):
            return result

        # Step 6: Proof Verification
        if not self._step6_proof_structure_validation(bundle_dict, result):
            return result

        # Step 7: AI-ID Verification
        if not self._step7_ai_id_verification(bundle_dict, result):
            return result

        # Step 8: Data Commitment Verification
        if not self._step8_data_commitment_verification(bundle_dict, result):
            return result

        # Step 9: Timestamp Verification (optional)
        legal = bundle_dict.get("legal")
        if legal and legal.get("timestamp_authority"):
            if not self._step9_timestamp_verification(bundle_dict, result):
                result.status = VerificationStatus.VALID_PARTIAL

        # Step 10: Proof Graph Verification (optional)
        proof_graph = bundle_dict.get("proof_graph")
        if proof_graph and proof_graph.get("depends_on"):
            if not self._step10_proof_graph_verification(bundle_dict, result):
                result.status = VerificationStatus.VALID_PARTIAL

        # Final status
        if result.status == VerificationStatus.VALID and not result.errors:
            result.is_valid = True
        else:
            result.is_valid = False

        return result

    def _step1_version_check(self, bundle: Dict[str, Any], result: VerificationResult) -> bool:
        """Step 1: Check vrl_version == "1.0"."""
        vrl_version = bundle.get("vrl_version")
        if vrl_version != "1.0":
            detail = VerificationDetail(
                step="§12.1 Version Check",
                status="FAIL",
                message=f"Unsupported vrl_version: {vrl_version}",
                error_code=VerificationStatus.UNSUPPORTED_VERSION
            )
            result.details.append(detail)
            result.errors.append(VerificationStatus.UNSUPPORTED_VERSION)
            result.status = VerificationStatus.UNSUPPORTED_VERSION
            result.is_valid = False
            return False

        detail = VerificationDetail(
            step="§12.1 Version Check",
            status="PASS",
            message=f"vrl_version {vrl_version} is supported"
        )
        result.details.append(detail)
        return True

    def _step2_schema_validation(self, bundle: Dict[str, Any], result: VerificationResult) -> bool:
        """Step 2: Validate against JSON Schema."""
        required_fields = [
            "bundle_id", "vrl_version", "issued_at", "ai_identity", "computation", "proof"
        ]
        for field in required_fields:
            if field not in bundle:
                detail = VerificationDetail(
                    step="§12.2 Schema Validation",
                    status="FAIL",
                    message=f"Required field missing: {field}",
                    error_code=VerificationStatus.SCHEMA_INVALID
                )
                result.details.append(detail)
                result.errors.append(VerificationStatus.SCHEMA_INVALID)
                result.status = VerificationStatus.SCHEMA_INVALID
                result.is_valid = False
                return False

        # Check ai_identity
        ai_identity = bundle.get("ai_identity", {})
        if not self._is_valid_hex_hash(ai_identity.get("ai_id")):
            detail = VerificationDetail(
                step="§12.2 Schema Validation",
                status="FAIL",
                message=f"Invalid ai_id format",
                error_code=VerificationStatus.SCHEMA_INVALID
            )
            result.details.append(detail)
            result.errors.append(VerificationStatus.SCHEMA_INVALID)
            result.status = VerificationStatus.SCHEMA_INVALID
            result.is_valid = False
            return False

        # Check computation hashes
        computation = bundle.get("computation", {})
        hash_fields = ["circuit_hash", "input_hash", "output_hash", "trace_hash", "integrity_hash"]
        for field in hash_fields:
            if not self._is_valid_hex_hash(computation.get(field)):
                detail = VerificationDetail(
                    step="§12.2 Schema Validation",
                    status="FAIL",
                    message=f"Invalid {field} format",
                    error_code=VerificationStatus.SCHEMA_INVALID
                )
                result.details.append(detail)
                result.errors.append(VerificationStatus.SCHEMA_INVALID)
                result.status = VerificationStatus.SCHEMA_INVALID
                result.is_valid = False
                return False

        # Check proof
        proof = bundle.get("proof", {})
        if not self._is_valid_hex_hash(proof.get("proof_hash")):
            detail = VerificationDetail(
                step="§12.2 Schema Validation",
                status="FAIL",
                message=f"Invalid proof_hash format",
                error_code=VerificationStatus.SCHEMA_INVALID
            )
            result.details.append(detail)
            result.errors.append(VerificationStatus.SCHEMA_INVALID)
            result.status = VerificationStatus.SCHEMA_INVALID
            result.is_valid = False
            return False

        detail = VerificationDetail(
            step="§12.2 Schema Validation",
            status="PASS",
            message="All required fields present and valid"
        )
        result.details.append(detail)
        return True

    def _step3_bundle_id_check(self, bundle: Dict[str, Any], result: VerificationResult) -> bool:
        """Step 3: Recompute and verify bundle_id."""
        integrity_hash = bundle.get("computation", {}).get("integrity_hash")
        try:
            namespace_uuid = uuid.UUID(self.VRL_NAMESPACE_UUID)
            recomputed_uuid = uuid.uuid5(namespace_uuid, integrity_hash)
            recomputed_bundle_id = str(recomputed_uuid)
        except Exception as e:
            detail = VerificationDetail(
                step="§12.3 bundle_id Recomputation",
                status="FAIL",
                message=f"Could not recompute bundle_id: {e}",
                error_code=VerificationStatus.BUNDLE_ID_MISMATCH
            )
            result.details.append(detail)
            result.errors.append(VerificationStatus.BUNDLE_ID_MISMATCH)
            result.status = VerificationStatus.BUNDLE_ID_MISMATCH
            result.is_valid = False
            return False

        stored_bundle_id = bundle.get("bundle_id")
        if recomputed_bundle_id != stored_bundle_id:
            detail = VerificationDetail(
                step="§12.3 bundle_id Recomputation",
                status="FAIL",
                message=f"bundle_id mismatch",
                error_code=VerificationStatus.BUNDLE_ID_MISMATCH,
                computed_value=recomputed_bundle_id,
                expected_value=stored_bundle_id
            )
            result.details.append(detail)
            result.errors.append(VerificationStatus.BUNDLE_ID_MISMATCH)
            result.status = VerificationStatus.BUNDLE_ID_MISMATCH
            result.is_valid = False
            return False

        detail = VerificationDetail(
            step="§12.3 bundle_id Recomputation",
            status="PASS",
            message=f"bundle_id {stored_bundle_id} is valid",
            computed_value=recomputed_bundle_id
        )
        result.details.append(detail)
        return True

    def _step4_integrity_hash_check(self, bundle: Dict[str, Any], result: VerificationResult) -> bool:
        """Step 4: Recompute integrity_hash."""
        computation = bundle.get("computation", {})
        input_hash = computation.get("input_hash")
        output_hash = computation.get("output_hash")
        trace_hash = computation.get("trace_hash")
        stored_integrity = computation.get("integrity_hash")

        recomputed_integrity = compute_integrity_hash(input_hash, output_hash, trace_hash)

        if recomputed_integrity != stored_integrity:
            detail = VerificationDetail(
                step="§12.4 Integrity Hash Recomputation",
                status="FAIL",
                message="integrity_hash mismatch",
                error_code=VerificationStatus.INTEGRITY_MISMATCH,
                computed_value=recomputed_integrity,
                expected_value=stored_integrity
            )
            result.details.append(detail)
            result.errors.append(VerificationStatus.INTEGRITY_MISMATCH)
            result.status = VerificationStatus.INTEGRITY_MISMATCH
            result.is_valid = False
            return False

        detail = VerificationDetail(
            step="§12.4 Integrity Hash Recomputation",
            status="PASS",
            message=f"integrity_hash verified",
            computed_value=recomputed_integrity
        )
        result.details.append(detail)
        return True

    def _step5_circuit_resolution(self, bundle: Dict[str, Any], result: VerificationResult) -> bool:
        """Step 5: Resolve circuit and verify circuit_hash."""
        computation = bundle.get("computation", {})
        circuit_id = computation.get("circuit_id")
        circuit_version = computation.get("circuit_version")
        stored_circuit_hash = computation.get("circuit_hash")

        circuit = self.registry.resolve_circuit(circuit_id, circuit_version)

        if circuit is None:
            detail = VerificationDetail(
                step="§12.5 Circuit Registry Lookup",
                status="FAIL",
                message=f"Circuit not found: {circuit_id}@{circuit_version}",
                error_code=VerificationStatus.CIRCUIT_HASH_MISMATCH
            )
            result.details.append(detail)
            result.errors.append(VerificationStatus.CIRCUIT_HASH_MISMATCH)
            result.status = VerificationStatus.CIRCUIT_HASH_MISMATCH
            result.is_valid = False
            return False

        computed_circuit_hash = circuit.get("circuit_hash")
        if computed_circuit_hash != stored_circuit_hash:
            detail = VerificationDetail(
                step="§12.5 Circuit Registry Lookup",
                status="FAIL",
                message=f"circuit_hash mismatch",
                error_code=VerificationStatus.CIRCUIT_HASH_MISMATCH,
                computed_value=computed_circuit_hash,
                expected_value=stored_circuit_hash
            )
            result.details.append(detail)
            result.errors.append(VerificationStatus.CIRCUIT_HASH_MISMATCH)
            result.status = VerificationStatus.CIRCUIT_HASH_MISMATCH
            result.is_valid = False
            return False

        detail = VerificationDetail(
            step="§12.5 Circuit Registry Lookup",
            status="PASS",
            message=f"Circuit {circuit_id} verified",
            computed_value=computed_circuit_hash
        )
        result.details.append(detail)
        return True

    def _step6_proof_structure_validation(self, bundle: Dict[str, Any], result: VerificationResult) -> bool:
        """Step 6: Proof structure validation."""
        proof = bundle.get("proof", {})
        computation = bundle.get("computation", {})

        # Validate proof_system
        valid_systems = {
            "plonk-halo2-pasta", "plonk-halo2-bn254",
            "groth16-bn254", "stark", "zk-ml",
            "tee-intel-tdx", "tee-amd-sev-snp", "tee-aws-nitro",
            "sha256-deterministic", "api-hash-binding"
        }
        proof_system = proof.get("proof_system")
        if proof_system not in valid_systems:
            detail = VerificationDetail(
                step="§12.6 Proof Verification",
                status="FAIL",
                message=f"Invalid proof_system: {proof_system}",
                error_code=VerificationStatus.PROOF_INVALID
            )
            result.details.append(detail)
            result.errors.append(VerificationStatus.PROOF_INVALID)
            result.status = VerificationStatus.PROOF_INVALID
            result.is_valid = False
            return False

        # Recompute proof_hash
        circuit_hash = computation.get("circuit_hash")
        proof_bytes = proof.get("proof_bytes", "")
        public_inputs = proof.get("public_inputs", [])
        trace_hash = computation.get("trace_hash")
        stored_proof_hash = proof.get("proof_hash")

        recomputed_proof_hash = compute_proof_hash(
            circuit_hash, proof_bytes, public_inputs, proof_system, trace_hash
        )

        if recomputed_proof_hash != stored_proof_hash:
            detail = VerificationDetail(
                step="§12.6 Proof Verification",
                status="FAIL",
                message=f"proof_hash mismatch",
                error_code=VerificationStatus.PROOF_INVALID,
                computed_value=recomputed_proof_hash,
                expected_value=stored_proof_hash
            )
            result.details.append(detail)
            result.errors.append(VerificationStatus.PROOF_INVALID)
            result.status = VerificationStatus.PROOF_INVALID
            result.is_valid = False
            return False

        detail = VerificationDetail(
            step="§12.6 Proof Verification",
            status="PASS",
            message=f"Proof structure valid for {proof_system}",
            computed_value=recomputed_proof_hash
        )
        result.details.append(detail)
        return True

    def _step7_ai_id_verification(self, bundle: Dict[str, Any], result: VerificationResult) -> bool:
        """Step 7: AI-ID verification."""
        ai_identity = bundle.get("ai_identity", {})
        ai_id = ai_identity.get("ai_id")

        if not self._is_valid_hex_hash(ai_id):
            detail = VerificationDetail(
                step="§12.7 AI-ID Verification",
                status="FAIL",
                message=f"Invalid ai_id format",
                error_code=VerificationStatus.AI_ID_INVALID
            )
            result.details.append(detail)
            result.errors.append(VerificationStatus.AI_ID_INVALID)
            result.status = VerificationStatus.AI_ID_INVALID
            result.is_valid = False
            return False

        # If no provider signature, just verify format
        if not ai_identity.get("provider_signature"):
            detail = VerificationDetail(
                step="§12.7 AI-ID Verification",
                status="PASS",
                message="AI-ID format valid (no provider_signature; AI-ID is advisory only)"
            )
            result.details.append(detail)
            return True

        detail = VerificationDetail(
            step="§12.7 AI-ID Verification",
            status="PASS",
            message="AI-ID valid (provider_signature present but not verified in standalone mode)"
        )
        result.details.append(detail)
        return True

    def _step8_data_commitment_verification(self, bundle: Dict[str, Any], result: VerificationResult) -> bool:
        """Step 8: Data commitment verification."""
        commitments = bundle.get("data_commitments", [])

        if not commitments:
            detail = VerificationDetail(
                step="§12.8 Data Commitment Signatures",
                status="PASS",
                message="No data commitments"
            )
            result.details.append(detail)
            return True

        for i, commitment in enumerate(commitments):
            dataset_id = commitment.get("dataset_id")
            dataset_version = commitment.get("dataset_version")
            dataset_hash = commitment.get("dataset_hash")
            provider_id = commitment.get("provider_id")
            committed_at = commitment.get("committed_at")
            stored_commitment_hash = commitment.get("commitment_hash")

            recomputed_hash = compute_commitment_hash(
                dataset_id, dataset_version, dataset_hash, provider_id, committed_at
            )

            if recomputed_hash != stored_commitment_hash:
                detail = VerificationDetail(
                    step=f"§12.8 Data Commitment Signatures [{i}]",
                    status="FAIL",
                    message=f"commitment_hash mismatch for {dataset_id}",
                    error_code=VerificationStatus.DATA_COMMITMENT_INVALID,
                    computed_value=recomputed_hash,
                    expected_value=stored_commitment_hash
                )
                result.details.append(detail)
                result.errors.append(VerificationStatus.DATA_COMMITMENT_INVALID)
                result.status = VerificationStatus.DATA_COMMITMENT_INVALID
                result.is_valid = False
                return False

        detail = VerificationDetail(
            step="§12.8 Data Commitment Signatures",
            status="PASS",
            message=f"All {len(commitments)} data commitments verified"
        )
        result.details.append(detail)
        return True

    def _step9_timestamp_verification(self, bundle: Dict[str, Any], result: VerificationResult) -> bool:
        """Step 9: Timestamp verification (optional)."""
        legal = bundle.get("legal", {})
        tsa = legal.get("timestamp_authority", {})

        if not tsa:
            return True

        tsa_token = tsa.get("tsa_token")
        tsa_provider = tsa.get("tsa_provider")
        tsa_hash_algorithm = tsa.get("tsa_hash_algorithm")

        if not (tsa_token and tsa_provider and tsa_hash_algorithm):
            detail = VerificationDetail(
                step="§12.9 Timestamp Validation",
                status="FAIL",
                message="Incomplete timestamp_authority block",
                error_code=VerificationStatus.TIMESTAMP_INVALID
            )
            result.details.append(detail)
            result.errors.append(VerificationStatus.TIMESTAMP_INVALID)
            return False

        detail = VerificationDetail(
            step="§12.9 Timestamp Validation",
            status="PASS",
            message=f"Timestamp token from {tsa_provider} (RFC 3161 verification skipped in standalone mode)"
        )
        result.details.append(detail)
        return True

    def _step10_proof_graph_verification(self, bundle: Dict[str, Any], result: VerificationResult) -> bool:
        """Step 10: Proof graph verification (optional)."""
        proof_graph = bundle.get("proof_graph", {})
        depends_on = proof_graph.get("depends_on", [])

        if not depends_on:
            return True

        for bundle_id in depends_on:
            try:
                uuid.UUID(bundle_id)
            except (ValueError, AttributeError):
                detail = VerificationDetail(
                    step="§12.10 Output Envelope Binding",
                    status="FAIL",
                    message=f"Invalid bundle_id in depends_on: {bundle_id}",
                    error_code=VerificationStatus.GRAPH_EDGE_INVALID
                )
                result.details.append(detail)
                result.errors.append(VerificationStatus.GRAPH_EDGE_INVALID)
                return False

        detail = VerificationDetail(
            step="§12.10 Output Envelope Binding",
            status="PASS",
            message=f"Proof graph edges valid (recursive verification skipped in standalone mode)"
        )
        result.details.append(detail)
        return True

    @staticmethod
    def _is_valid_hex_hash(value: Any) -> bool:
        """Check if value is a valid 64-character lowercase hex string."""
        if not isinstance(value, str):
            return False
        if len(value) != 64:
            return False
        try:
            int(value, 16)
            return value == value.lower()
        except (ValueError, TypeError):
            return False


# ============================================================================
# TERMINAL OUTPUT FORMATTING
# ============================================================================

class TerminalFormatter:
    """Format verification results for human-readable terminal output."""

    # ANSI color codes
    GREEN = '\033[92m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[90m'
    RESET = '\033[0m'

    @staticmethod
    def _disable_colors_if_needed() -> None:
        """Disable colors if output is not a TTY."""
        if not sys.stdout.isatty():
            TerminalFormatter.GREEN = ''
            TerminalFormatter.RED = ''
            TerminalFormatter.BOLD = ''
            TerminalFormatter.DIM = ''
            TerminalFormatter.RESET = ''

    @classmethod
    def format_result(cls, result: VerificationResult, bundle: Dict[str, Any], verbose: bool = False) -> str:
        """Format verification result as a human-readable report."""
        cls._disable_colors_if_needed()

        lines = []
        lines.append("")
        lines.append(f"{cls.BOLD}VRL Proof Bundle Verifier v1.0{cls.RESET}")
        lines.append("=" * 50)

        # Bundle header
        ai_identity = bundle.get("ai_identity", {})
        computation = bundle.get("computation", {})
        proof = bundle.get("proof", {})

        model_name = ai_identity.get("model_name", "unknown")
        proof_system = proof.get("proof_system", "unknown")
        circuit_id = computation.get("circuit_id", "unknown")

        lines.append(f"{cls.BOLD}Bundle ID:{cls.RESET}  {result.bundle_id}")
        lines.append(f"{cls.BOLD}AI Model:{cls.RESET}   {model_name}")
        lines.append(f"{cls.BOLD}Proof:{cls.RESET}      {proof_system}")
        lines.append(f"{cls.BOLD}Circuit:{cls.RESET}    {circuit_id}")
        lines.append("")

        # Verification steps
        lines.append(f"{cls.BOLD}VERIFICATION STEPS{cls.RESET}")
        lines.append("-" * 50)

        for detail in result.details:
            status_str = f"{cls.GREEN}[PASS]{cls.RESET}" if detail.status == "PASS" else f"{cls.RED}[FAIL]{cls.RESET}"
            lines.append(f"{status_str} {detail.step}")
            lines.append(f"       {detail.message}")

            if verbose and detail.computed_value:
                lines.append(f"       {cls.DIM}computed: {detail.computed_value[:32]}...{cls.RESET}")
            if verbose and detail.expected_value:
                lines.append(f"       {cls.DIM}expected: {detail.expected_value[:32]}...{cls.RESET}")

        lines.append("")

        # Final result
        if result.is_valid:
            result_str = f"{cls.GREEN}VALID ✓{cls.RESET}"
        else:
            result_str = f"{cls.RED}INVALID ✗{cls.RESET}"

        lines.append(f"{cls.BOLD}RESULT: {result_str}{cls.RESET}")
        lines.append("=" * 50)

        return "\n".join(lines)


# ============================================================================
# MAIN
# ============================================================================

def main() -> int:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Standalone VRL Proof Bundle Verifier (Spec §12)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python vrl_verify.py bundle.json
  python vrl_verify.py bundle.json --verbose
  python vrl_verify.py bundle.json --json-output
  cat bundle.json | python vrl_verify.py

Exit codes:
  0 — VALID or VALID_PARTIAL
  1 — INVALID
  2 — ERROR (bad input)
        """.strip()
    )

    parser.add_argument(
        "bundle",
        nargs="?",
        help="Path to VRL proof bundle JSON file (or stdin if omitted)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show hash values and intermediate computations"
    )
    parser.add_argument(
        "--json-output", "-j",
        action="store_true",
        help="Output machine-readable JSON result"
    )

    args = parser.parse_args()

    # Load bundle JSON
    try:
        if args.bundle:
            with open(args.bundle, 'r') as f:
                bundle = json.load(f)
        else:
            bundle = json.load(sys.stdin)
    except FileNotFoundError:
        print(f"Error: File not found: {args.bundle}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    # Run verification
    verifier = Verifier(verbose=args.verbose)
    result = verifier.verify(bundle)

    # Output result
    if args.json_output:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(TerminalFormatter.format_result(result, bundle, verbose=args.verbose))

    # Exit code
    if result.is_valid:
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
