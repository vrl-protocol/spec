from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from backend.proof_export import export_proof_bundle, verify_proof_bundle, write_proof_bundle  # noqa: E402
from core.sample import REFERENCE_REQUEST  # noqa: E402


def main() -> int:
  bundle = export_proof_bundle(REFERENCE_REQUEST)
  write_proof_bundle(ROOT / 'logs' / 'smoke_proof_bundle.json', bundle)
  verification = verify_proof_bundle(bundle)
  output = {
    'input_hash': bundle['input_hash'],
    'trace_hash': bundle['trace_hash'],
    'circuit_hash': bundle['circuit_hash'],
    'proof_valid': verification['valid'],
  }
  print(json.dumps(output, indent=2))
  return 0 if verification['valid'] else 1


if __name__ == '__main__':
  raise SystemExit(main())
