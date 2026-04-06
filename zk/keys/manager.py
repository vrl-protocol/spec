"""Deterministic key management for the Halo2 proving backend.

The Rust backend is the source of truth for actual key generation. Python keeps a
stable manifest layer keyed by circuit_hash so the rest of the pipeline stays
artifact-driven and deterministic.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from zk.compiler.plonk_adapter import PlonkCircuit, compile_circuit
from zk.rust_bridge import BACKEND_VERSION, KEY_ROOT, run_backend


@dataclass(frozen=True)
class ProvingKey:
  circuit_hash: str
  proving_key_id: str
  manifest_path: Path
  version: str
  params_k: int


@dataclass(frozen=True)
class VerificationKey:
  circuit_hash: str
  verification_key_id: str
  manifest_path: Path
  version: str
  params_k: int


@dataclass(frozen=True)
class KeyMaterial:
  circuit_hash: str
  proving_key_id: str
  verification_key_id: str
  params_k: int
  proving_manifest_path: Path
  verification_manifest_path: Path
  version: str


class KeyManager:
  @classmethod
  def keys_root(cls) -> Path:
    KEY_ROOT.mkdir(parents=True, exist_ok=True)
    (KEY_ROOT / 'proving_key').mkdir(parents=True, exist_ok=True)
    (KEY_ROOT / 'verification_key').mkdir(parents=True, exist_ok=True)
    return KEY_ROOT

  @classmethod
  def ensure_compiled(cls, circuit: PlonkCircuit | None = None) -> KeyMaterial:
    resolved_circuit = circuit or compile_circuit()
    cls.keys_root()
    response = run_backend(
      'compile',
      {
        'circuit_hash': resolved_circuit.circuit_hash,
        'version': resolved_circuit.version,
        'binding_targets': list(resolved_circuit.public_binding_targets),
        'constraint_count': resolved_circuit.n_gates,
        'key_root': str(KEY_ROOT),
      },
      timeout=300,
    )
    from zk.keys.lifecycle import log_key_generation
    log_key_generation(
      circuit_hash=response['circuit_hash'],
      proving_key_id=response['proving_key_id'],
      verification_key_id=response['verification_key_id'],
      params_k=int(response['params_k']),
      backend_version=response.get('backend_version', BACKEND_VERSION),
    )
    return KeyMaterial(
      circuit_hash=response['circuit_hash'],
      proving_key_id=response['proving_key_id'],
      verification_key_id=response['verification_key_id'],
      params_k=int(response['params_k']),
      proving_manifest_path=Path(response['proving_manifest_path']),
      verification_manifest_path=Path(response['verification_manifest_path']),
      version=response.get('backend_version', BACKEND_VERSION),
    )

  @classmethod
  def derive_proving_key(cls, circuit_hash: str, selectors: dict[str, list[int]] | None = None, circuit: PlonkCircuit | None = None) -> ProvingKey:
    resolved_circuit = circuit or compile_circuit()
    if resolved_circuit.circuit_hash != circuit_hash:
      raise ValueError(f'Circuit hash mismatch: expected {resolved_circuit.circuit_hash}, got {circuit_hash}')
    material = cls.ensure_compiled(resolved_circuit)
    return ProvingKey(
      circuit_hash=material.circuit_hash,
      proving_key_id=material.proving_key_id,
      manifest_path=material.proving_manifest_path,
      version=material.version,
      params_k=material.params_k,
    )

  @classmethod
  def derive_verification_key(cls, circuit_hash: str, selectors: dict[str, list[int]] | None = None, circuit: PlonkCircuit | None = None) -> VerificationKey:
    resolved_circuit = circuit or compile_circuit()
    if resolved_circuit.circuit_hash != circuit_hash:
      raise ValueError(f'Circuit hash mismatch: expected {resolved_circuit.circuit_hash}, got {circuit_hash}')
    material = cls.ensure_compiled(resolved_circuit)
    return VerificationKey(
      circuit_hash=material.circuit_hash,
      verification_key_id=material.verification_key_id,
      manifest_path=material.verification_manifest_path,
      version=material.version,
      params_k=material.params_k,
    )
