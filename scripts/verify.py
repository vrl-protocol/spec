from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.verifier import verify_proof  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description='Verify a Verifiable Reality Layer proof artifact')
    parser.add_argument('--request', required=True, type=Path)
    parser.add_argument('--response', required=True, type=Path)
    args = parser.parse_args()

    request_payload = json.loads(args.request.read_text(encoding='utf-8'))
    response_payload = json.loads(args.response.read_text(encoding='utf-8'))
    result = verify_proof(request_payload, response_payload)
    print(result.model_dump_json(indent=2))
    return 0 if result.status == 'VALID' else 1


if __name__ == '__main__':
    raise SystemExit(main())
