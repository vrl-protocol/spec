from __future__ import annotations

import asyncio
import json
import os
import ssl
from dataclasses import dataclass

import asyncpg


@dataclass(frozen=True)
class DatabaseSettings:
    url: str
    min_pool_size: int = 1
    max_pool_size: int = 20          # raised from 5; tunable via VRL_DB_MAX_POOL_SIZE
    command_timeout_seconds: float = 5.0
    connect_timeout_seconds: float = 5.0
    retry_attempts: int = 3
    retry_backoff_seconds: float = 0.25
    require_tls: bool = True
    ssl_ca_file: str | None = None   # path to CA cert; None = system trust store
    statement_timeout_ms: int = 5000
    lock_timeout_ms: int = 5000

    @classmethod
    def from_env(cls) -> 'DatabaseSettings | None':
        url = os.getenv('VRL_DATABASE_URL')
        if not url:
            return None
        return cls(
            url=url,
            min_pool_size=int(os.getenv('VRL_DB_MIN_POOL_SIZE', '1')),
            max_pool_size=int(os.getenv('VRL_DB_MAX_POOL_SIZE', '20')),
            command_timeout_seconds=float(os.getenv('VRL_DB_COMMAND_TIMEOUT_SECONDS', '5')),
            connect_timeout_seconds=float(os.getenv('VRL_DB_CONNECT_TIMEOUT_SECONDS', '5')),
            retry_attempts=int(os.getenv('VRL_DB_RETRY_ATTEMPTS', '3')),
            retry_backoff_seconds=float(os.getenv('VRL_DB_RETRY_BACKOFF_SECONDS', '0.25')),
            require_tls=os.getenv('VRL_DB_REQUIRE_TLS', 'true').lower() == 'true',
            ssl_ca_file=os.getenv('VRL_DB_SSL_CA') or None,
            statement_timeout_ms=int(os.getenv('VRL_DB_STATEMENT_TIMEOUT_MS', '5000')),
            lock_timeout_ms=int(os.getenv('VRL_DB_LOCK_TIMEOUT_MS', '5000')),
        )


class TLSEnforcementError(RuntimeError):
    """Raised at startup when TLS is disabled outside of development mode."""


def _ssl_context(settings: DatabaseSettings) -> ssl.SSLContext | None:
    """Build an SSL context for verify-full TLS.

    Raises TLSEnforcementError if TLS is disabled and VRL_ALLOW_PLAINTEXT is
    not explicitly set to "true" (development override only).
    """
    if not settings.require_tls:
        allow_plaintext = os.getenv("VRL_ALLOW_PLAINTEXT", "false").lower() == "true"
        if not allow_plaintext:
            raise TLSEnforcementError(
                "TLS is required (VRL_DB_REQUIRE_TLS=true by default). "
                "Set VRL_ALLOW_PLAINTEXT=true only in local development."
            )
        return None
    context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    if settings.ssl_ca_file:
        context.load_verify_locations(cafile=settings.ssl_ca_file)
    return context


async def _init_connection(connection: asyncpg.Connection) -> None:
    await connection.set_type_codec(
        'jsonb',
        schema='pg_catalog',
        encoder=lambda value: json.dumps(value),
        decoder=json.loads,
        format='text',
    )


async def create_pool(settings: DatabaseSettings) -> asyncpg.Pool:
    ssl_context = _ssl_context(settings)

    # Set statement_timeout and lock_timeout at connection-init time so that
    # every session inherits them without paying two extra round-trips per
    # transaction.  The per-transaction SET calls in PostgresRepositoryTransaction
    # have been removed; these server_settings replace them.
    server_settings = {
        'statement_timeout': str(settings.statement_timeout_ms),
        'lock_timeout': str(settings.lock_timeout_ms),
    }

    last_error: Exception | None = None
    for attempt in range(1, settings.retry_attempts + 1):
        try:
            return await asyncpg.create_pool(
                dsn=settings.url,
                min_size=settings.min_pool_size,
                max_size=settings.max_pool_size,
                command_timeout=settings.command_timeout_seconds,
                timeout=settings.connect_timeout_seconds,
                ssl=ssl_context,
                init=_init_connection,
                server_settings=server_settings,
            )
        except Exception as exc:
            last_error = exc
            if attempt == settings.retry_attempts:
                raise
            await asyncio.sleep(settings.retry_backoff_seconds)
    if last_error is not None:
        raise last_error
    raise RuntimeError('Unable to create database pool')


async def close_pool(pool: asyncpg.Pool | None) -> None:
    if pool is not None:
        await pool.close()
