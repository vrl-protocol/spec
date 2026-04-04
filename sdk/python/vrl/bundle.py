"""
Core ProofBundle class for VRL Proof Bundles.

Implements the complete structure specified in VRL Spec §3 with serialization support.
"""

import json
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
from .identity import AIIdentity
from .hashing import canonical_json


@dataclass
class Computation:
    """Computation record with hashed artefacts (VRL Spec §3.5)."""

    circuit_id: str
    circuit_version: str
    circuit_hash: str
    input_hash: str
    output_hash: str
    trace_hash: str
    integrity_hash: str

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "Computation":
        """Create from dictionary."""
        required = {
            "circuit_id", "circuit_version", "circuit_hash",
            "input_hash", "output_hash", "trace_hash", "integrity_hash"
        }
        if not required.issubset(data.keys()):
            missing = required - set(data.keys())
            raise ValueError(f"Missing required computation fields: {missing}")
        return Computation(**{k: data[k] for k in required})


@dataclass
class Proof:
    """Proof object with ZK or TEE data (VRL Spec §3.7)."""

    proof_system: str
    proof_bytes: str
    public_inputs: List[str]
    verification_key_id: str
    proof_hash: str
    commitments: Optional[List[str]] = None

    def to_dict(self) -> dict:
        """Convert to dictionary, omitting None fields."""
        result = asdict(self)
        return {k: v for k, v in result.items() if v is not None}

    @staticmethod
    def from_dict(data: dict) -> "Proof":
        """Create from dictionary."""
        required = {
            "proof_system", "proof_bytes", "public_inputs",
            "verification_key_id", "proof_hash"
        }
        if not required.issubset(data.keys()):
            missing = required - set(data.keys())
            raise ValueError(f"Missing required proof fields: {missing}")

        # Validate proof_system
        valid_systems = {
            "plonk-halo2-pasta", "plonk-halo2-bn254",
            "groth16-bn254", "stark", "zk-ml",
            "tee-intel-tdx", "tee-amd-sev-snp", "tee-aws-nitro",
            "sha256-deterministic", "api-hash-binding"
        }
        if data["proof_system"] not in valid_systems:
            raise ValueError(f"Invalid proof_system: {data['proof_system']}")

        return Proof(
            proof_system=data["proof_system"],
            proof_bytes=data["proof_bytes"],
            public_inputs=data["public_inputs"],
            verification_key_id=data["verification_key_id"],
            proof_hash=data["proof_hash"],
            commitments=data.get("commitments")
        )


@dataclass
class DataCommitment:
    """Data commitment binding computation to dataset version (VRL Spec §6.2)."""

    dataset_id: str
    dataset_version: str
    dataset_hash: str
    provider_id: str
    committed_at: str
    commitment_hash: str
    provider_signature: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary, omitting None fields."""
        result = asdict(self)
        return {k: v for k, v in result.items() if v is not None}

    @staticmethod
    def from_dict(data: dict) -> "DataCommitment":
        """Create from dictionary."""
        required = {
            "dataset_id", "dataset_version", "dataset_hash",
            "provider_id", "committed_at", "commitment_hash"
        }
        if not required.issubset(data.keys()):
            missing = required - set(data.keys())
            raise ValueError(f"Missing required data commitment fields: {missing}")
        return DataCommitment(
            dataset_id=data["dataset_id"],
            dataset_version=data["dataset_version"],
            dataset_hash=data["dataset_hash"],
            provider_id=data["provider_id"],
            committed_at=data["committed_at"],
            commitment_hash=data["commitment_hash"],
            provider_signature=data.get("provider_signature")
        )


@dataclass
class TimestampAuthority:
    """RFC 3161 timestamp authority block (VRL Spec §8.5)."""

    tsa_token: str
    tsa_provider: str
    tsa_hash_algorithm: str

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "TimestampAuthority":
        """Create from dictionary."""
        return TimestampAuthority(**data)


@dataclass
class ImmutableAnchor:
    """Blockchain anchor for timestamp proofing (VRL Spec §8.6)."""

    chain: str
    tx_hash: str
    block_number: int
    anchored_at: str

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "ImmutableAnchor":
        """Create from dictionary."""
        return ImmutableAnchor(**data)


@dataclass
class Legal:
    """Legal metadata and compliance claims (VRL Spec §8)."""

    jurisdictions: Optional[List[str]] = None
    admissibility_standard: Optional[str] = None
    compliance_flags: Optional[List[str]] = None
    timestamp_authority: Optional[TimestampAuthority] = None
    immutable_anchor: Optional[ImmutableAnchor] = None

    def to_dict(self) -> dict:
        """Convert to dictionary, omitting None fields."""
        result = {
            "jurisdictions": self.jurisdictions,
            "admissibility_standard": self.admissibility_standard,
            "compliance_flags": self.compliance_flags
        }
        if self.timestamp_authority:
            result["timestamp_authority"] = self.timestamp_authority.to_dict()
        if self.immutable_anchor:
            result["immutable_anchor"] = self.immutable_anchor.to_dict()
        return {k: v for k, v in result.items() if v is not None}

    @staticmethod
    def from_dict(data: dict) -> "Legal":
        """Create from dictionary."""
        tsa = None
        if "timestamp_authority" in data and data["timestamp_authority"]:
            tsa = TimestampAuthority.from_dict(data["timestamp_authority"])
        anchor = None
        if "immutable_anchor" in data and data["immutable_anchor"]:
            anchor = ImmutableAnchor.from_dict(data["immutable_anchor"])
        return Legal(
            jurisdictions=data.get("jurisdictions"),
            admissibility_standard=data.get("admissibility_standard"),
            compliance_flags=data.get("compliance_flags"),
            timestamp_authority=tsa,
            immutable_anchor=anchor
        )


@dataclass
class ProofGraph:
    """Directed acyclic proof graph for causal dependencies (VRL Spec §7)."""

    depends_on: Optional[List[str]] = None
    produced_by: Optional[str] = None
    causal_depth: Optional[int] = None
    graph_root_hash: Optional[str] = None
    privacy_tier: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary, omitting None fields."""
        result = asdict(self)
        return {k: v for k, v in result.items() if v is not None}

    @staticmethod
    def from_dict(data: dict) -> "ProofGraph":
        """Create from dictionary."""
        return ProofGraph(
            depends_on=data.get("depends_on"),
            produced_by=data.get("produced_by"),
            causal_depth=data.get("causal_depth"),
            graph_root_hash=data.get("graph_root_hash"),
            privacy_tier=data.get("privacy_tier")
        )


@dataclass
class TrustContext:
    """Trust score and anomaly data at issuance (VRL Spec §9)."""

    prover_id: Optional[str] = None
    prover_version: Optional[str] = None
    trust_score_at_issuance: Optional[float] = None
    circuit_certification_tier: Optional[str] = None
    anomaly_flags: Optional[List[str]] = None

    def to_dict(self) -> dict:
        """Convert to dictionary, omitting None fields."""
        result = asdict(self)
        return {k: v for k, v in result.items() if v is not None}

    @staticmethod
    def from_dict(data: dict) -> "TrustContext":
        """Create from dictionary."""
        return TrustContext(
            prover_id=data.get("prover_id"),
            prover_version=data.get("prover_version"),
            trust_score_at_issuance=data.get("trust_score_at_issuance"),
            circuit_certification_tier=data.get("circuit_certification_tier"),
            anomaly_flags=data.get("anomaly_flags")
        )


@dataclass
class ProofBundle:
    """
    Complete VRL Proof Bundle as specified in VRL Spec §3.

    A portable, self-contained artifact that cryptographically attests to
    the identity, inputs, outputs, and execution correctness of any AI system
    or deterministic computation.

    Attributes:
        vrl_version: Spec version (must be "1.0")
        bundle_id: Deterministic UUIDv5 from integrity_hash
        issued_at: RFC 3339 timestamp of proof generation
        ai_identity: AI identity claim with model info
        computation: Hashed artefacts of computation
        proof: Cryptographic proof or attestation
        data_commitments: Optional array of dataset commitments
        legal: Optional legal metadata and compliance claims
        proof_graph: Optional causal dependency graph
        trust_context: Optional trust score and anomaly flags
    """

    vrl_version: str
    bundle_id: str
    issued_at: str
    ai_identity: AIIdentity
    computation: Computation
    proof: Proof
    data_commitments: Optional[List[DataCommitment]] = None
    legal: Optional[Legal] = None
    proof_graph: Optional[ProofGraph] = None
    trust_context: Optional[TrustContext] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert ProofBundle to dictionary representation.

        Returns:
            Dictionary with all bundle fields, omitting None optional fields
        """
        result = {
            "vrl_version": self.vrl_version,
            "bundle_id": self.bundle_id,
            "issued_at": self.issued_at,
            "ai_identity": self.ai_identity.to_dict(),
            "computation": self.computation.to_dict(),
            "proof": self.proof.to_dict()
        }

        if self.data_commitments:
            result["data_commitments"] = [dc.to_dict() for dc in self.data_commitments]
        if self.legal:
            result["legal"] = self.legal.to_dict()
        if self.proof_graph:
            result["proof_graph"] = self.proof_graph.to_dict()
        if self.trust_context:
            result["trust_context"] = self.trust_context.to_dict()

        return result

    def to_json(self, pretty: bool = False) -> str:
        """
        Serialize ProofBundle to JSON string.

        Args:
            pretty: If True, format with indentation for readability.
                   If False, use compact canonical format.

        Returns:
            JSON string representation
        """
        bundle_dict = self.to_dict()
        if pretty:
            return json.dumps(bundle_dict, indent=2, sort_keys=True)
        else:
            # Use canonical serialization for integrity/verification
            return canonical_json(bundle_dict)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ProofBundle":
        """
        Create ProofBundle from dictionary.

        Args:
            data: Dictionary with all required and optional fields

        Returns:
            ProofBundle instance

        Raises:
            ValueError: If required fields are missing or invalid
        """
        required_fields = {
            "vrl_version", "bundle_id", "issued_at",
            "ai_identity", "computation", "proof"
        }
        if not required_fields.issubset(data.keys()):
            missing = required_fields - set(data.keys())
            raise ValueError(f"Missing required bundle fields: {missing}")

        # Validate vrl_version
        if data["vrl_version"] != "1.0":
            raise ValueError(f"Unsupported vrl_version: {data['vrl_version']}")

        # Parse nested objects
        ai_identity = AIIdentity.from_dict(data["ai_identity"])
        computation = Computation.from_dict(data["computation"])
        proof = Proof.from_dict(data["proof"])

        # Optional fields
        data_commitments = None
        if "data_commitments" in data and data["data_commitments"]:
            data_commitments = [
                DataCommitment.from_dict(dc) for dc in data["data_commitments"]
            ]

        legal = None
        if "legal" in data and data["legal"]:
            legal = Legal.from_dict(data["legal"])

        proof_graph = None
        if "proof_graph" in data and data["proof_graph"]:
            proof_graph = ProofGraph.from_dict(data["proof_graph"])

        trust_context = None
        if "trust_context" in data and data["trust_context"]:
            trust_context = TrustContext.from_dict(data["trust_context"])

        return ProofBundle(
            vrl_version=data["vrl_version"],
            bundle_id=data["bundle_id"],
            issued_at=data["issued_at"],
            ai_identity=ai_identity,
            computation=computation,
            proof=proof,
            data_commitments=data_commitments,
            legal=legal,
            proof_graph=proof_graph,
            trust_context=trust_context
        )

    @staticmethod
    def from_json(json_str: str) -> "ProofBundle":
        """
        Deserialize ProofBundle from JSON string.

        Args:
            json_str: JSON string representation

        Returns:
            ProofBundle instance

        Raises:
            ValueError: If JSON is invalid or doesn't conform to schema
        """
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")
        return ProofBundle.from_dict(data)
