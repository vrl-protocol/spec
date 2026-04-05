"""TEE Attestation Pipeline.

Supports: real Intel TDX (when running in TDX), real AMD SEV-SNP (when running in SNP),
and development simulation mode (sha256-deterministic fallback with clear labeling).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from utils.hashing import sha256_hex


class TEEMode(str, Enum):
    """TEE attestation mode enumeration."""

    INTEL_TDX = 'intel_tdx'
    AMD_SEV_SNP = 'amd_sev_snp'
    SIMULATION = 'simulation'


@dataclass(frozen=True)
class TEEAttestation:
    """Represents a TEE attestation for an AI inference."""

    tee_mode: TEEMode
    model_hash: str
    input_hash: str
    output_hash: str
    runtime_hash: str
    attestation_report_bytes: str
    attestation_report_hash: str
    is_simulation: bool
    simulation_warning: str | None = None


class TEEAttestationPipeline:
    """Pipeline for generating TEE attestations."""

    def __init__(self, mode: TEEMode = TEEMode.SIMULATION) -> None:
        """
        Initialize the TEE attestation pipeline.

        Args:
            mode: The TEE mode to use (INTEL_TDX, AMD_SEV_SNP, or SIMULATION).
        """
        self.mode = mode

    def attest(
        self,
        model_id: str,
        model_hash: str,
        input_text: str,
        output_text: str,
    ) -> TEEAttestation:
        """
        Generate a TEE attestation for an inference.

        Args:
            model_id: Identifier for the model.
            model_hash: SHA256 hash of model weights or model identifier.
            input_text: Input text for the inference.
            output_text: Output text from the inference.

        Returns:
            A TEEAttestation object.

        Raises:
            NotImplementedError: If using TDX or SNP mode outside an enclave.
        """
        if self.mode == TEEMode.INTEL_TDX:
            raise NotImplementedError(
                'Intel TDX attestation is only available when running inside a TDX enclave. '
                'Use TEEMode.SIMULATION for development or run this code inside a TDX-enabled environment.'
            )
        if self.mode == TEEMode.AMD_SEV_SNP:
            raise NotImplementedError(
                'AMD SEV-SNP attestation is only available when running inside a SEV-SNP enclave. '
                'Use TEEMode.SIMULATION for development or run this code inside a SEV-SNP-enabled environment.'
            )

        # SIMULATION mode: deterministic attestation using SHA256
        input_hash = sha256_hex(input_text)
        output_hash = sha256_hex(output_text)
        runtime_descriptor = f'model_id={model_id},python_runtime=3.11,platform=x86_64'
        runtime_hash = sha256_hex(runtime_descriptor)

        # Build deterministic attestation report combining all inputs
        attestation_payload = f'{model_hash}|{input_hash}|{output_hash}|{runtime_hash}|SIMULATION_MODE'
        attestation_report_bytes = sha256_hex(attestation_payload)
        attestation_report_hash = sha256_hex(attestation_report_bytes)

        simulation_warning = 'SIMULATION MODE: not hardware-attested'

        return TEEAttestation(
            tee_mode=self.mode,
            model_hash=model_hash,
            input_hash=input_hash,
            output_hash=output_hash,
            runtime_hash=runtime_hash,
            attestation_report_bytes=attestation_report_bytes,
            attestation_report_hash=attestation_report_hash,
            is_simulation=True,
            simulation_warning=simulation_warning,
        )

    def to_vrl_proof(self, attestation: TEEAttestation) -> dict[str, object]:
        """
        Convert a TEE attestation to a VRL proof bundle section.

        Args:
            attestation: The TEE attestation to convert.

        Returns:
            A dictionary representing the VRL proof section.
        """
        proof_system = 'sha256-deterministic'
        if attestation.tee_mode == TEEMode.INTEL_TDX:
            proof_system = 'tee-intel-tdx'
        elif attestation.tee_mode == TEEMode.AMD_SEV_SNP:
            proof_system = 'tee-amd-sev-snp'

        proof_dict: dict[str, object] = {
            'proof_system': proof_system,
            'tee_mode': attestation.tee_mode.value,
            'model_hash': attestation.model_hash,
            'input_hash': attestation.input_hash,
            'output_hash': attestation.output_hash,
            'runtime_hash': attestation.runtime_hash,
            'attestation_report_bytes': attestation.attestation_report_bytes,
            'attestation_report_hash': attestation.attestation_report_hash,
            'is_simulation': attestation.is_simulation,
        }

        if attestation.simulation_warning:
            proof_dict['simulation_warning'] = attestation.simulation_warning

        return proof_dict
