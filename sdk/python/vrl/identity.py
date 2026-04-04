"""
AI Identity module for VRL Proof Bundles.

Implements AI-ID computation and identity claims as specified in VRL Spec §2.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional
from .hashing import compute_ai_id as _compute_ai_id, sha256, canonical_json


@dataclass
class AIIdentity:
    """
    Represents an AI identity claim in a VRL Proof Bundle.

    Attributes:
        ai_id: SHA-256 hash uniquely identifying this AI model at this version
               in this execution environment (64 hex characters)
        model_name: Human-readable name of the model
        model_version: Semantic version of the model
        provider_id: Canonical identifier of the provider (e.g. "com.openai")
        execution_environment: One of: "deterministic", "tee", "zk-ml",
                              "api-attested", "unattested"
        provider_signature: Optional base64-encoded Ed25519 signature over ai_id
        tee_attestation_report: Optional base64-encoded TEE attestation report
                               (REQUIRED if execution_environment == "tee")
        parent_ai_id: Optional SHA-256 of parent AI-ID for lineage tracking
    """

    ai_id: str
    model_name: str
    model_version: str
    provider_id: str
    execution_environment: str
    provider_signature: Optional[str] = None
    tee_attestation_report: Optional[str] = None
    parent_ai_id: Optional[str] = None

    def to_dict(self) -> dict:
        """
        Convert AIIdentity to dictionary, omitting None fields.

        Returns:
            Dictionary representation
        """
        result = asdict(self)
        return {k: v for k, v in result.items() if v is not None}

    @staticmethod
    def from_dict(data: dict) -> "AIIdentity":
        """
        Create AIIdentity from dictionary.

        Args:
            data: Dictionary with ai_identity fields

        Returns:
            AIIdentity instance

        Raises:
            ValueError: If required fields are missing or invalid
        """
        required_fields = {
            "ai_id", "model_name", "model_version",
            "provider_id", "execution_environment"
        }
        if not required_fields.issubset(data.keys()):
            missing = required_fields - set(data.keys())
            raise ValueError(f"Missing required fields: {missing}")

        # Validate ai_id format (64 hex characters)
        if not _is_valid_hex_hash(data["ai_id"]):
            raise ValueError(f"Invalid ai_id format: {data['ai_id']}")

        # Validate execution_environment
        valid_envs = {"deterministic", "tee", "zk-ml", "api-attested", "unattested"}
        if data["execution_environment"] not in valid_envs:
            raise ValueError(
                f"Invalid execution_environment: {data['execution_environment']}"
            )

        return AIIdentity(
            ai_id=data["ai_id"],
            model_name=data["model_name"],
            model_version=data["model_version"],
            provider_id=data["provider_id"],
            execution_environment=data["execution_environment"],
            provider_signature=data.get("provider_signature"),
            tee_attestation_report=data.get("tee_attestation_report"),
            parent_ai_id=data.get("parent_ai_id")
        )


class AIIdentityBuilder:
    """
    Fluent builder for creating AIIdentity instances with optional fields.
    """

    def __init__(self):
        """Initialize builder with no fields set."""
        self._ai_id: Optional[str] = None
        self._model_name: Optional[str] = None
        self._model_version: Optional[str] = None
        self._provider_id: Optional[str] = None
        self._execution_environment: Optional[str] = None
        self._provider_signature: Optional[str] = None
        self._tee_attestation_report: Optional[str] = None
        self._parent_ai_id: Optional[str] = None

    def compute_ai_id(
        self,
        model_weights_hash: str,
        runtime_hash: str,
        config_hash: str,
        provider_id: str,
        model_name: str,
        model_version: str
    ) -> "AIIdentityBuilder":
        """
        Compute and set the AI-ID using the specified parameters.

        Implements VRL Spec §2.2 AI-ID computation.

        Args:
            model_weights_hash: SHA-256 of model weights
            runtime_hash: SHA-256 of runtime environment descriptor
            config_hash: SHA-256 of inference config
            provider_id: Provider canonical name
            model_name: Model name
            model_version: Semantic version

        Returns:
            Self for chaining
        """
        self._ai_id = _compute_ai_id(
            model_weights_hash, runtime_hash, config_hash,
            provider_id, model_name, model_version
        )
        self._provider_id = provider_id
        self._model_name = model_name
        self._model_version = model_version
        return self

    def set_ai_id(self, ai_id: str) -> "AIIdentityBuilder":
        """Set the AI-ID directly (64 hex characters)."""
        if not _is_valid_hex_hash(ai_id):
            raise ValueError(f"Invalid ai_id format: {ai_id}")
        self._ai_id = ai_id
        return self

    def set_model_name(self, model_name: str) -> "AIIdentityBuilder":
        """Set the model name."""
        self._model_name = model_name
        return self

    def set_model_version(self, model_version: str) -> "AIIdentityBuilder":
        """Set the model semantic version."""
        self._model_version = model_version
        return self

    def set_provider_id(self, provider_id: str) -> "AIIdentityBuilder":
        """Set the provider canonical ID."""
        self._provider_id = provider_id
        return self

    def set_execution_environment(self, env: str) -> "AIIdentityBuilder":
        """
        Set the execution environment.

        Args:
            env: One of "deterministic", "tee", "zk-ml", "api-attested", "unattested"

        Returns:
            Self for chaining
        """
        valid_envs = {"deterministic", "tee", "zk-ml", "api-attested", "unattested"}
        if env not in valid_envs:
            raise ValueError(f"Invalid execution_environment: {env}")
        self._execution_environment = env
        return self

    def set_provider_signature(self, sig: str) -> "AIIdentityBuilder":
        """Set the provider Ed25519 signature (base64)."""
        self._provider_signature = sig
        return self

    def set_tee_attestation_report(self, report: str) -> "AIIdentityBuilder":
        """Set the TEE attestation report (base64)."""
        self._tee_attestation_report = report
        return self

    def set_parent_ai_id(self, parent_ai_id: str) -> "AIIdentityBuilder":
        """Set the parent AI-ID for lineage tracking."""
        if not _is_valid_hex_hash(parent_ai_id):
            raise ValueError(f"Invalid parent_ai_id format: {parent_ai_id}")
        self._parent_ai_id = parent_ai_id
        return self

    def build(self) -> AIIdentity:
        """
        Build and return the AIIdentity.

        Returns:
            AIIdentity instance

        Raises:
            ValueError: If required fields are not set
        """
        required = [
            self._ai_id, self._model_name, self._model_version,
            self._provider_id, self._execution_environment
        ]
        if any(x is None for x in required):
            raise ValueError(
                "Missing required fields for AIIdentity. "
                "Must set: ai_id, model_name, model_version, provider_id, "
                "execution_environment"
            )

        return AIIdentity(
            ai_id=self._ai_id,
            model_name=self._model_name,
            model_version=self._model_version,
            provider_id=self._provider_id,
            execution_environment=self._execution_environment,
            provider_signature=self._provider_signature,
            tee_attestation_report=self._tee_attestation_report,
            parent_ai_id=self._parent_ai_id
        )


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
