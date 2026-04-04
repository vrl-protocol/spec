"""
Fluent builder API for constructing VRL Proof Bundles.

Provides a convenient fluent interface for building complex bundles incrementally.
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import uuid

from .bundle import (
    ProofBundle, AIIdentity, Computation, Proof,
    DataCommitment, Legal, ProofGraph, TrustContext,
    TimestampAuthority, ImmutableAnchor
)
from .identity import AIIdentity as AIIdentityClass, AIIdentityBuilder
from .hashing import compute_bundle_id_from_integrity


class ProofBundleBuilder:
    """
    Fluent builder for constructing VRL Proof Bundles.

    Example usage:
        bundle = (ProofBundleBuilder()
            .set_ai_identity(identity)
            .set_computation(...)
            .set_proof(...)
            .set_legal(...)
            .build())
    """

    def __init__(self):
        """Initialize builder with empty state."""
        self._vrl_version = "1.0"
        self._bundle_id: Optional[str] = None
        self._issued_at: Optional[str] = None
        self._ai_identity: Optional[AIIdentity] = None
        self._computation: Optional[Computation] = None
        self._proof: Optional[Proof] = None
        self._data_commitments: List[DataCommitment] = []
        self._legal: Optional[Legal] = None
        self._proof_graph: Optional[ProofGraph] = None
        self._trust_context: Optional[TrustContext] = None

    def set_vrl_version(self, version: str) -> "ProofBundleBuilder":
        """Set VRL specification version (default: "1.0")."""
        self._vrl_version = version
        return self

    def set_bundle_id(self, bundle_id: str) -> "ProofBundleBuilder":
        """
        Set bundle_id explicitly (normally computed from integrity_hash).

        Args:
            bundle_id: UUID string

        Returns:
            Self for chaining
        """
        self._bundle_id = bundle_id
        return self

    def set_issued_at(self, issued_at: str) -> "ProofBundleBuilder":
        """
        Set issued_at timestamp (RFC 3339 format).

        Args:
            issued_at: RFC 3339 timestamp (e.g. "2026-04-04T12:00:00.000Z")

        Returns:
            Self for chaining
        """
        self._issued_at = issued_at
        return self

    def set_issued_at_now(self) -> "ProofBundleBuilder":
        """Set issued_at to current UTC time."""
        now = datetime.now(timezone.utc)
        self._issued_at = now.isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        return self

    def set_ai_identity(self, ai_identity: AIIdentity) -> "ProofBundleBuilder":
        """
        Set the AI identity claim.

        Args:
            ai_identity: AIIdentity instance

        Returns:
            Self for chaining
        """
        self._ai_identity = ai_identity
        return self

    def set_ai_identity_from_dict(self, data: dict) -> "ProofBundleBuilder":
        """
        Set AI identity from dictionary.

        Args:
            data: Dictionary with ai_identity fields

        Returns:
            Self for chaining
        """
        self._ai_identity = AIIdentity.from_dict(data)
        return self

    def set_computation(self, computation: Computation) -> "ProofBundleBuilder":
        """
        Set the computation record with hashes.

        Args:
            computation: Computation instance

        Returns:
            Self for chaining
        """
        self._computation = computation
        return self

    def set_computation_from_dict(self, data: dict) -> "ProofBundleBuilder":
        """
        Set computation from dictionary.

        Args:
            data: Dictionary with computation fields

        Returns:
            Self for chaining
        """
        self._computation = Computation.from_dict(data)
        return self

    def set_proof(self, proof: Proof) -> "ProofBundleBuilder":
        """
        Set the cryptographic proof.

        Args:
            proof: Proof instance

        Returns:
            Self for chaining
        """
        self._proof = proof
        return self

    def set_proof_from_dict(self, data: dict) -> "ProofBundleBuilder":
        """
        Set proof from dictionary.

        Args:
            data: Dictionary with proof fields

        Returns:
            Self for chaining
        """
        self._proof = Proof.from_dict(data)
        return self

    def add_data_commitment(self, commitment: DataCommitment) -> "ProofBundleBuilder":
        """
        Add a data commitment.

        Args:
            commitment: DataCommitment instance

        Returns:
            Self for chaining
        """
        self._data_commitments.append(commitment)
        return self

    def add_data_commitment_from_dict(self, data: dict) -> "ProofBundleBuilder":
        """
        Add a data commitment from dictionary.

        Args:
            data: Dictionary with data commitment fields

        Returns:
            Self for chaining
        """
        self._data_commitments.append(DataCommitment.from_dict(data))
        return self

    def set_legal(self, legal: Legal) -> "ProofBundleBuilder":
        """
        Set legal metadata and compliance claims.

        Args:
            legal: Legal instance

        Returns:
            Self for chaining
        """
        self._legal = legal
        return self

    def set_legal_from_dict(self, data: dict) -> "ProofBundleBuilder":
        """
        Set legal metadata from dictionary.

        Args:
            data: Dictionary with legal fields

        Returns:
            Self for chaining
        """
        self._legal = Legal.from_dict(data)
        return self

    def set_proof_graph(self, proof_graph: ProofGraph) -> "ProofBundleBuilder":
        """
        Set proof graph for causal dependencies.

        Args:
            proof_graph: ProofGraph instance

        Returns:
            Self for chaining
        """
        self._proof_graph = proof_graph
        return self

    def set_proof_graph_from_dict(self, data: dict) -> "ProofBundleBuilder":
        """
        Set proof graph from dictionary.

        Args:
            data: Dictionary with proof_graph fields

        Returns:
            Self for chaining
        """
        self._proof_graph = ProofGraph.from_dict(data)
        return self

    def set_trust_context(self, trust_context: TrustContext) -> "ProofBundleBuilder":
        """
        Set trust context with trust score and anomaly flags.

        Args:
            trust_context: TrustContext instance

        Returns:
            Self for chaining
        """
        self._trust_context = trust_context
        return self

    def set_trust_context_from_dict(self, data: dict) -> "ProofBundleBuilder":
        """
        Set trust context from dictionary.

        Args:
            data: Dictionary with trust_context fields

        Returns:
            Self for chaining
        """
        self._trust_context = TrustContext.from_dict(data)
        return self

    def build(self) -> ProofBundle:
        """
        Build and return the ProofBundle.

        Returns:
            ProofBundle instance

        Raises:
            ValueError: If required fields are not set
        """
        # Check required fields
        if self._ai_identity is None:
            raise ValueError("ai_identity is required")
        if self._computation is None:
            raise ValueError("computation is required")
        if self._proof is None:
            raise ValueError("proof is required")

        # Set issued_at if not provided
        if self._issued_at is None:
            self.set_issued_at_now()

        # Compute bundle_id if not provided
        if self._bundle_id is None:
            from .hashing import compute_bundle_id_from_integrity
            self._bundle_id = compute_bundle_id_from_integrity(
                self._computation.integrity_hash
            )

        return ProofBundle(
            vrl_version=self._vrl_version,
            bundle_id=self._bundle_id,
            issued_at=self._issued_at,
            ai_identity=self._ai_identity,
            computation=self._computation,
            proof=self._proof,
            data_commitments=self._data_commitments if self._data_commitments else None,
            legal=self._legal,
            proof_graph=self._proof_graph,
            trust_context=self._trust_context
        )


class ComputationBuilder:
    """Fluent builder for Computation objects."""

    def __init__(self):
        """Initialize computation builder."""
        self._circuit_id: Optional[str] = None
        self._circuit_version: Optional[str] = None
        self._circuit_hash: Optional[str] = None
        self._input_hash: Optional[str] = None
        self._output_hash: Optional[str] = None
        self._trace_hash: Optional[str] = None
        self._integrity_hash: Optional[str] = None

    def set_circuit_id(self, circuit_id: str) -> "ComputationBuilder":
        """Set circuit registry identifier."""
        self._circuit_id = circuit_id
        return self

    def set_circuit_version(self, version: str) -> "ComputationBuilder":
        """Set circuit semantic version."""
        self._circuit_version = version
        return self

    def set_circuit_hash(self, hash_value: str) -> "ComputationBuilder":
        """Set circuit hash (SHA-256 hex)."""
        self._circuit_hash = hash_value
        return self

    def set_input_hash(self, hash_value: str) -> "ComputationBuilder":
        """Set input hash (SHA-256 hex)."""
        self._input_hash = hash_value
        return self

    def set_output_hash(self, hash_value: str) -> "ComputationBuilder":
        """Set output hash (SHA-256 hex)."""
        self._output_hash = hash_value
        return self

    def set_trace_hash(self, hash_value: str) -> "ComputationBuilder":
        """Set trace hash (SHA-256 hex)."""
        self._trace_hash = hash_value
        return self

    def set_integrity_hash(self, hash_value: str) -> "ComputationBuilder":
        """Set integrity hash (SHA-256 hex)."""
        self._integrity_hash = hash_value
        return self

    def compute_integrity_hash(self) -> "ComputationBuilder":
        """
        Compute integrity_hash from input, output, and trace hashes.

        Returns:
            Self for chaining
        """
        if self._input_hash is None or self._output_hash is None or self._trace_hash is None:
            raise ValueError("Must set input_hash, output_hash, and trace_hash first")
        from .hashing import compute_integrity_hash
        self._integrity_hash = compute_integrity_hash(
            self._input_hash, self._output_hash, self._trace_hash
        )
        return self

    def build(self) -> Computation:
        """
        Build and return the Computation.

        Returns:
            Computation instance

        Raises:
            ValueError: If required fields are not set
        """
        required_fields = [
            (self._circuit_id, "circuit_id"),
            (self._circuit_version, "circuit_version"),
            (self._circuit_hash, "circuit_hash"),
            (self._input_hash, "input_hash"),
            (self._output_hash, "output_hash"),
            (self._trace_hash, "trace_hash"),
            (self._integrity_hash, "integrity_hash"),
        ]
        missing = [name for value, name in required_fields if value is None]
        if missing:
            raise ValueError(f"Missing required computation fields: {missing}")

        return Computation(
            circuit_id=self._circuit_id,
            circuit_version=self._circuit_version,
            circuit_hash=self._circuit_hash,
            input_hash=self._input_hash,
            output_hash=self._output_hash,
            trace_hash=self._trace_hash,
            integrity_hash=self._integrity_hash
        )


class ProofBuilder:
    """Fluent builder for Proof objects."""

    def __init__(self):
        """Initialize proof builder."""
        self._proof_system: Optional[str] = None
        self._proof_bytes: Optional[str] = None
        self._public_inputs: Optional[List[str]] = None
        self._verification_key_id: Optional[str] = None
        self._proof_hash: Optional[str] = None
        self._commitments: Optional[List[str]] = None

    def set_proof_system(self, system: str) -> "ProofBuilder":
        """Set proof system identifier."""
        self._proof_system = system
        return self

    def set_proof_bytes(self, proof_bytes: str) -> "ProofBuilder":
        """Set hex-encoded proof bytes."""
        self._proof_bytes = proof_bytes
        return self

    def set_public_inputs(self, inputs: List[str]) -> "ProofBuilder":
        """Set array of hex-encoded public inputs."""
        self._public_inputs = inputs
        return self

    def set_verification_key_id(self, key_id: str) -> "ProofBuilder":
        """Set verification key ID (SHA-256 hex)."""
        self._verification_key_id = key_id
        return self

    def set_proof_hash(self, hash_value: str) -> "ProofBuilder":
        """Set proof hash (SHA-256 hex)."""
        self._proof_hash = hash_value
        return self

    def set_commitments(self, commitments: List[str]) -> "ProofBuilder":
        """Set optional commitments array."""
        self._commitments = commitments
        return self

    def build(self) -> Proof:
        """
        Build and return the Proof.

        Returns:
            Proof instance

        Raises:
            ValueError: If required fields are not set
        """
        required_fields = [
            (self._proof_system, "proof_system"),
            (self._proof_bytes, "proof_bytes"),
            (self._public_inputs, "public_inputs"),
            (self._verification_key_id, "verification_key_id"),
            (self._proof_hash, "proof_hash"),
        ]
        missing = [name for value, name in required_fields if value is None]
        if missing:
            raise ValueError(f"Missing required proof fields: {missing}")

        return Proof(
            proof_system=self._proof_system,
            proof_bytes=self._proof_bytes,
            public_inputs=self._public_inputs,
            verification_key_id=self._verification_key_id,
            proof_hash=self._proof_hash,
            commitments=self._commitments
        )
