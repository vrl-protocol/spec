from __future__ import annotations

"""Legacy module retained only to fail closed.

The PostgreSQL audit chain is the sole forensic source of truth for this system.
File-based audit logging is intentionally disabled to prevent split-brain evidence.
"""


class LegacyAuditLogDisabledError(RuntimeError):
    """Raised when legacy file-based audit logging is invoked."""


ERROR_MESSAGE = (
    'File-based audit logging is disabled. Use the PostgreSQL append-only audit_log '
    'table and the database-backed verification flow instead.'
)


def ensure_audit_log() -> None:
    raise LegacyAuditLogDisabledError(ERROR_MESSAGE)


def append_audit_record(*, input_hash: str, output_hash: str, result_hash: str, final_proof: str):
    raise LegacyAuditLogDisabledError(ERROR_MESSAGE)
