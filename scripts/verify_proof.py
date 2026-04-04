from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from backend.proof_export import verify_proof_bundle  # noqa: E402


def main(argv: list[str]) -> int:
  if len(argv) != 2:
    print(json.dumps({'valid': False, 'reason': 'usage: python scripts/verify_proof.py proof_bundle.json'}))
    return 2
  bundle_path = Path(argv[1])
  try:
    bundle = json.loads(bundle_path.read_text(encoding='utf-8'))
  except FileNotFoundError:
    print(json.dumps({'valid': False, 'reason': f'proof bundle not found: {bundle_path}'}, indent=2))
    return 1
  except json.JSONDecodeError as exc:
    print(json.dumps({'valid': False, 'reason': f'invalid bundle json: {exc}'}, indent=2))
    return 1
  result = verify_proof_bundle(bundle)
  print(json.dumps({'valid': result['valid'], 'reason': result['reason']}, indent=2))
  return 0 if result['valid'] else 1


if __name__ == '__main__':
  raise SystemExit(main(sys.argv))
