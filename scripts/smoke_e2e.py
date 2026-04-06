from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from backend.proof_export import export_proof_bundle, verify_proof_bundle, write_proof_bundle  # noqa: E402
from core.sample import REFERENCE_REQUEST  # noqa: E402


def _parse_args(argv: list[str]) -> argparse.Namespace:
  parser = argparse.ArgumentParser(description='Run the VRL reference proof pipeline end to end.')
  parser.add_argument(
    '--output',
    default=str(ROOT / 'logs' / 'smoke_proof_bundle.json'),
    help='Path to write the generated proof bundle JSON.',
  )
  return parser.parse_args(argv)


def _determinism_report(bundle_a: dict[str, object], bundle_b: dict[str, object]) -> dict[str, object]:
  checks = {
    'input_hash': bundle_a['input_hash'] == bundle_b['input_hash'],
    'output_hash': bundle_a['output_hash'] == bundle_b['output_hash'],
    'trace_hash': bundle_a['trace_hash'] == bundle_b['trace_hash'],
    'circuit_hash': bundle_a['circuit_hash'] == bundle_b['circuit_hash'],
    'verification_key_hash': bundle_a['verification_key_hash'] == bundle_b['verification_key_hash'],
    'proof_blob_hex': bundle_a['proof']['proof_blob_hex'] == bundle_b['proof']['proof_blob_hex'],
    'final_proof': bundle_a['proof']['final_proof'] == bundle_b['proof']['final_proof'],
  }
  return {
    'all_match': all(checks.values()),
    'checks': checks,
  }


def main(argv: list[str] | None = None) -> int:
  args = _parse_args(argv or [])
  bundle_a = export_proof_bundle(REFERENCE_REQUEST)
  bundle_b = export_proof_bundle(REFERENCE_REQUEST)
  output_path = write_proof_bundle(args.output, bundle_a)
  verification = verify_proof_bundle(bundle_a)
  determinism = _determinism_report(bundle_a, bundle_b)
  output = {
    'output_path': str(output_path),
    'verification': {
      'valid': verification['valid'],
      'reason': verification['reason'],
    },
    'determinism': determinism,
    'bundle_summary': {
      'input_hash': bundle_a['input_hash'],
      'output_hash': bundle_a['output_hash'],
      'trace_hash': bundle_a['trace_hash'],
      'circuit_hash': bundle_a['circuit_hash'],
      'verification_key_hash': bundle_a['verification_key_hash'],
      'proof_system': bundle_a['proof']['proof_system'],
    },
  }
  print(json.dumps(output, indent=2))
  return 0 if verification['valid'] and determinism['all_match'] else 1


if __name__ == '__main__':
  raise SystemExit(main(sys.argv[1:]))
