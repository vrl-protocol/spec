from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from app.db.connection import DatabaseSettings, TLSEnforcementError  # noqa: E402
from zk.rust_bridge import KEY_ROOT, PROJECT_ROOT, TARGET_BIN, _find_vcvars64  # noqa: E402


def main() -> int:
  checks: dict[str, object] = {
    'project_root': str(PROJECT_ROOT),
    'project_root_exists': PROJECT_ROOT.exists(),
    'rust_backend_binary': str(TARGET_BIN),
    'rust_backend_binary_exists': TARGET_BIN.exists(),
    'keys_root': str(KEY_ROOT),
    'keys_root_exists': KEY_ROOT.exists(),
  }

  if sys.platform.startswith('win'):
    vcvars = _find_vcvars64()
    checks['vcvars64'] = str(vcvars) if vcvars is not None else None
    checks['vcvars64_exists'] = vcvars.exists() if vcvars is not None else False

  db_settings = DatabaseSettings.from_env()
  if db_settings is None:
    checks['database_configured'] = False
    checks['required_env'] = {
      'VRL_DATABASE_URL': 'optional_for_local_verification',
    }
    checks['tls_readiness'] = 'not_applicable'
  else:
    checks['database_configured'] = True
    checks['required_env'] = {
      'VRL_DATABASE_URL': 'present',
      'VRL_DB_REQUIRE_TLS': str(db_settings.require_tls).lower(),
    }
    try:
      if db_settings.require_tls:
        checks['tls_readiness'] = 'configured'
      else:
        raise TLSEnforcementError(
          'TLS disabled; set VRL_ALLOW_PLAINTEXT=true only for local development'
        )
    except TLSEnforcementError as exc:
      checks['tls_readiness'] = f'failed: {exc}'

  ok = bool(checks['project_root_exists']) and bool(checks['rust_backend_binary_exists'])
  if db_settings is not None and str(checks['tls_readiness']).startswith('failed'):
    ok = False

  checks['valid'] = ok
  print(json.dumps(checks, indent=2))
  return 0 if ok else 1


if __name__ == '__main__':
  raise SystemExit(main())

