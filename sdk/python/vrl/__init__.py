"""
VRL SDK - Verifiable Reality Layer Python SDK

A complete implementation of the VRL Proof Bundle Specification v1.0.

This SDK provides:
- ProofBundle: Core data structure for VRL proof bundles
- Verifier: 10-step verification procedure per VRL Spec §12
- Builder APIs: Fluent interfaces for constructing bundles
- Hash utilities: SHA-256 and canonical JSON per VRL Spec §10-11
- Identity: AI-ID computation and verification per VRL Spec §2

Example:
    from vrl import ProofBundleBuilder, Verifier, ComputationBuilder

    # Build a bundle
    bundle = (ProofBundleBuilder()
        .set_ai_identity(ai_identity)
        .set_computation(computation)
        .set_proof(proof)
        .build())

    # Verify a bundle
    verifier = Verifier()
    result = verifier.verify(bundle)
    if result.is_valid:
        print("Bundle is valid!")
"""

__version__ = "0.1.0"
__author__ = "Verifiable Reality Layer Contributors"
__license__ = "CC BY 4.0"

# Core classes
from .bundle import (
    ProofBundle,
    Computation,
    Proof,
    DataCommitment,
    Legal,
    ProofGraph,
    TrustContext,
    TimestampAuthority,
    ImmutableAnchor,
    AIIdentity as BundleAIIdentity
)

# Identity
from .identity import (
    AIIdentity,
    AIIdentityBuilder
)

# Verification
from .verifier import (
    Verifier,
    VerificationResult,
    VerificationStatus,
    VerificationDetail,
    CircuitRegistry
)

# Builders
from .builder import (
    ProofBundleBuilder,
    ComputationBuilder,
    ProofBuilder
)

# Hash utilities
from .hashing import (
    canonical_json,
    sha256,
    compute_ai_id,
    compute_integrity_hash,
    compute_proof_hash,
    compute_input_hash,
    compute_output_hash,
    compute_trace_hash,
    compute_commitment_hash,
    compute_bundle_id_from_integrity
)

__all__ = [
    # Core
    "ProofBundle",
    "Computation",
    "Proof",
    "DataCommitment",
    "Legal",
    "ProofGraph",
    "TrustContext",
    "TimestampAuthority",
    "ImmutableAnchor",
    # Identity
    "AIIdentity",
    "AIIdentityBuilder",
    # Verification
    "Verifier",
    "VerificationResult",
    "VerificationStatus",
    "VerificationDetail",
    "CircuitRegistry",
    # Builders
    "ProofBundleBuilder",
    "ComputationBuilder",
    "ProofBuilder",
    # Hashing
    "canonical_json",
    "sha256",
    "compute_ai_id",
    "compute_integrity_hash",
    "compute_proof_hash",
    "compute_input_hash",
    "compute_output_hash",
    "compute_trace_hash",
    "compute_commitment_hash",
    "compute_bundle_id_from_integrity"
]
