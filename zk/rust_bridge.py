from __future__ import annotations

import json
import os
import subprocess  # nosec B404
from datetime import datetime, timezone
from pathlib import Path

from utils.canonical import canonical_json
from utils.hashing import sha256_hex

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUST_BACKEND_DIR = PROJECT_ROOT / 'zk' / 'rust_backend'
TARGET_BIN = RUST_BACKEND_DIR / 'target' / 'release' / ('vrl_halo2_backend.exe' if os.name == 'nt' else 'vrl_halo2_backend')
CARGO = Path.home() / '.cargo' / 'bin' / ('cargo.exe' if os.name == 'nt' else 'cargo')
CMD = Path(os.environ.get('ComSpec', r'C:\Windows\System32\cmd.exe')) if os.name == 'nt' else Path('/bin/sh')
KEY_ROOT = PROJECT_ROOT / 'zk' / 'keys'
FAILURE_LOG = PROJECT_ROOT / 'logs' / 'proof_failures.jsonl'
BACKEND_VERSION = 'halo2-plonk-pasta-v1'
VSWHERE = Path('C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe')
FALLBACK_VCVARS = Path('C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Auxiliary/Build/vcvars64.bat')


def _env_with_cargo() -> dict[str, str]:
  env = os.environ.copy()
  cargo_bin = str(CARGO.parent)
  env['PATH'] = cargo_bin + os.pathsep + env.get('PATH', '')
  return env


def _find_vcvars64() -> Path | None:
  if os.name != 'nt':
    return None
  if VSWHERE.exists():
    result = subprocess.run(  # nosec B603
      [
        str(VSWHERE),
        '-latest',
        '-products',
        '*',
        '-requires',
        'Microsoft.VisualStudio.Component.VC.Tools.x86.x64',
        '-property',
        'installationPath',
      ],
      capture_output=True,
      text=True,
      check=False,
    )
    installation_path = result.stdout.strip()
    if result.returncode == 0 and installation_path:
      candidate = Path(installation_path) / 'VC' / 'Auxiliary' / 'Build' / 'vcvars64.bat'
      if candidate.exists():
        return candidate
  if FALLBACK_VCVARS.exists():
    return FALLBACK_VCVARS
  return None


def ensure_backend_binary() -> Path:
  if TARGET_BIN.exists():
    return TARGET_BIN
  if not CARGO.exists():
    raise RuntimeError('Rust toolchain is not installed. Expected cargo at ' + str(CARGO))
  manifest_path = str(RUST_BACKEND_DIR / 'Cargo.toml')
  env = _env_with_cargo()
  if os.name == 'nt':
    vcvars64 = _find_vcvars64()
    if vcvars64 is not None:
      cargo_command = f'"{CARGO}" build --release --manifest-path "{manifest_path}"'
      result = subprocess.run(  # nosec B603
        [str(CMD), '/c', f'"{vcvars64}" && {cargo_command}'],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(RUST_BACKEND_DIR),
        check=False,
      )
    else:
      result = subprocess.run(  # nosec B603
        [str(CARGO), 'build', '--release', '--manifest-path', manifest_path],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(RUST_BACKEND_DIR),
        check=False,
      )
  else:
    result = subprocess.run(  # nosec B603
      [str(CARGO), 'build', '--release', '--manifest-path', manifest_path],
      capture_output=True,
      text=True,
      env=env,
      cwd=str(RUST_BACKEND_DIR),
      check=False,
    )
  if result.returncode != 0:
    raise RuntimeError('Rust backend build failed: ' + (result.stderr.strip() or result.stdout.strip()))
  if not TARGET_BIN.exists():
    raise RuntimeError('Rust backend build succeeded but the binary was not created')
  return TARGET_BIN


def _append_failure(stage: str, payload: dict[str, object], error: str) -> None:
  FAILURE_LOG.parent.mkdir(parents=True, exist_ok=True)
  record = {
    'recorded_at': datetime.now(timezone.utc).isoformat(),
    'stage': stage,
    'input_hash': payload.get('input_hash', ''),
    'trace_hash': payload.get('trace_hash', ''),
    'circuit_hash': payload.get('circuit_hash', ''),
    'error': error,
  }
  with FAILURE_LOG.open('a', encoding='utf-8', newline='\n') as handle:
    handle.write(canonical_json(record) + '\n')


def run_backend(command: str, payload: dict[str, object], *, timeout: int = 300) -> dict[str, object]:
  try:
    binary = ensure_backend_binary()
  except Exception as exc:
    error = f'native Halo2 backend unavailable: {exc}'
    _append_failure(command, payload, error)
    raise RuntimeError(error) from exc
  completed = subprocess.run(  # nosec B603
    [str(binary), command],
    input=canonical_json(payload),
    capture_output=True,
    text=True,
    timeout=timeout,
    env=_env_with_cargo(),
    cwd=str(PROJECT_ROOT),
    check=False,
  )
  if completed.returncode != 0:
    error = completed.stderr.strip() or completed.stdout.strip() or f'backend exited with code {completed.returncode}'
    _append_failure(command, payload, error)
    raise RuntimeError(error)
  try:
    response = json.loads(completed.stdout)
  except json.JSONDecodeError as exc:
    _append_failure(command, payload, f'invalid backend JSON: {exc}')
    raise RuntimeError('Rust backend returned invalid JSON') from exc
  return response


def public_inputs_hash(public_inputs: dict[str, str]) -> str:
  normalized = {key: str(value) for key, value in sorted(public_inputs.items())}
  return sha256_hex(canonical_json(normalized))
