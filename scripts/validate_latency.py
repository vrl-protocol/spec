"""
validate_latency.py
===================
Task 9 — Performance Validation

Measures p50 / p95 / p99 latency for the calculate_and_persist path under
100 concurrent coroutines.  Runs entirely in-process using the InMemory
repository so no live PostgreSQL is required, but also accepts an optional
VRL_DATABASE_URL to measure against a real pool.

Usage (in-memory):
    python scripts/validate_latency.py

Usage (real DB):
    $env:VRL_DATABASE_URL = "postgresql://vrl_writer:pw@localhost:5432/vrl_live"
    $env:VRL_DB_REQUIRE_TLS = "false"
    python scripts/validate_latency.py

Output:
    JSON report to stdout + docs/live-validation/latency_report.json
"""
from __future__ import annotations

import asyncio
import json
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.connection import DatabaseSettings, close_pool, create_pool  # noqa: E402
from app.db.repository import PostgresEvidenceRepository  # noqa: E402
from app.services.evidence_service import EvidenceService  # noqa: E402
from core.sample import REFERENCE_REQUEST  # noqa: E402
from tests.fakes import InMemoryEvidenceRepository  # noqa: E402

REPORT_DIR = ROOT / "docs" / "live-validation"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PATH = REPORT_DIR / "latency_report.json"

CONCURRENCY = 100
UNIQUE_INPUTS = 71
DUPLICATE_INPUTS = CONCURRENCY - UNIQUE_INPUTS  # 29


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    idx = max(0, min(len(ordered) - 1, round((p / 100) * (len(ordered) - 1))))
    return ordered[idx]


def build_payloads() -> list[dict]:
    """71 unique inputs + 29 duplicates of the first input."""
    payloads: list[dict] = []
    base = dict(REFERENCE_REQUEST)

    # unique inputs: vary quantity
    for i in range(UNIQUE_INPUTS):
        p = dict(base)
        p['quantity'] = i + 1
        payloads.append(p)

    # duplicates: repeat quantity=1 (same input_hash → replay protection)
    first = dict(base)
    first['quantity'] = 1
    for _ in range(DUPLICATE_INPUTS):
        payloads.append(dict(first))

    # shuffle via deterministic rotation so duplicates are interleaved
    result = []
    for i in range(CONCURRENCY):
        result.append(payloads[i % len(payloads)])
    return result


async def run_single(service: EvidenceService, payload: dict, timings: list[float]) -> str:
    t0 = time.perf_counter()
    try:
        await service.calculate_and_persist(payload)
        status = 'ok'
    except Exception as exc:
        status = type(exc).__name__
    elapsed_ms = (time.perf_counter() - t0) * 1000
    timings.append(elapsed_ms)
    return status


async def run_benchmark(service: EvidenceService, label: str) -> dict:
    payloads = build_payloads()
    timings: list[float] = []

    t_total_start = time.perf_counter()
    results = await asyncio.gather(
        *(run_single(service, p, timings) for p in payloads)
    )
    total_elapsed_ms = (time.perf_counter() - t_total_start) * 1000

    status_counts: dict[str, int] = {}
    for s in results:
        status_counts[s] = status_counts.get(s, 0) + 1

    chain_result = await service.verify_audit_chain()

    report = {
        'label': label,
        'concurrency': CONCURRENCY,
        'unique_inputs': UNIQUE_INPUTS,
        'duplicate_inputs': DUPLICATE_INPUTS,
        'total_wall_ms': round(total_elapsed_ms, 2),
        'throughput_rps': round(CONCURRENCY / (total_elapsed_ms / 1000), 1),
        'latency_ms': {
            'p50': round(percentile(timings, 50), 2),
            'p95': round(percentile(timings, 95), 2),
            'p99': round(percentile(timings, 99), 2),
            'min': round(min(timings), 2),
            'max': round(max(timings), 2),
            'mean': round(statistics.mean(timings), 2),
            'stdev': round(statistics.stdev(timings), 2) if len(timings) > 1 else 0.0,
        },
        'status_counts': status_counts,
        'audit_chain': {
            'status': chain_result.status,
            'checked_rows': chain_result.checked_rows,
            'reason': chain_result.reason,
        },
        'targets': {
            'p95_lt_100ms': percentile(timings, 95) < 100.0,
            'p95_lt_50ms': percentile(timings, 95) < 50.0,
            'audit_chain_valid': chain_result.status == 'VALID',
        },
    }
    return report


async def run_in_memory() -> dict:
    repository = InMemoryEvidenceRepository()
    service = EvidenceService(repository)
    return await run_benchmark(service, 'in-memory')


async def run_postgres(url: str) -> dict:
    settings = DatabaseSettings(
        url=url,
        min_pool_size=int(os.getenv('VRL_DB_MIN_POOL_SIZE', '1')),
        max_pool_size=int(os.getenv('VRL_DB_MAX_POOL_SIZE', '20')),
        require_tls=os.getenv('VRL_DB_REQUIRE_TLS', 'true').lower() == 'true',
        statement_timeout_ms=int(os.getenv('VRL_DB_STATEMENT_TIMEOUT_MS', '5000')),
        lock_timeout_ms=int(os.getenv('VRL_DB_LOCK_TIMEOUT_MS', '5000')),
    )
    pool = await create_pool(settings)
    try:
        repository = PostgresEvidenceRepository(
            pool,
            statement_timeout_ms=settings.statement_timeout_ms,
            lock_timeout_ms=settings.lock_timeout_ms,
            connect_timeout_seconds=settings.connect_timeout_seconds,
        )
        service = EvidenceService(repository)
        return await run_benchmark(service, 'postgresql')
    finally:
        await close_pool(pool)


async def run_replay_integrity(service: EvidenceService) -> dict:
    """Re-run verify_audit_chain + a spot verify_persisted to confirm integrity."""
    base = dict(REFERENCE_REQUEST)
    payload = dict(base)
    payload['quantity'] = 999

    await service.calculate_and_persist(payload)
    verify_result = await service.verify_persisted(payload)
    chain_result = await service.verify_audit_chain()

    return {
        'verify_persisted_status': verify_result.verification.status,
        'audit_chain_status': chain_result.status,
        'checked_rows': chain_result.checked_rows,
        'determinism': 'PASS' if verify_result.verification.status == 'VALID' else 'FAIL',
        'chain_integrity': 'PASS' if chain_result.status == 'VALID' else 'FAIL',
    }


def pass_fail(flag: bool) -> str:
    return 'PASS' if flag else 'FAIL'


async def main() -> None:
    db_url = os.getenv('VRL_DATABASE_URL')
    reports = []

    print('=== Verifiable Reality Layer — Latency Validation ===\n')

    # --- in-memory benchmark (baseline) ---
    print('Running in-memory benchmark (100 concurrent)...')
    mem_report = await run_in_memory()
    reports.append(mem_report)
    _print_report(mem_report)

    # --- PostgreSQL benchmark (if configured) ---
    if db_url:
        print('\nRunning PostgreSQL benchmark (100 concurrent)...')
        pg_report = await run_postgres(db_url)
        reports.append(pg_report)
        _print_report(pg_report)

        # replay integrity on postgres
        settings = DatabaseSettings(
            url=db_url,
            max_pool_size=5,
            require_tls=os.getenv('VRL_DB_REQUIRE_TLS', 'true').lower() == 'true',
        )
        pool = await create_pool(settings)
        repo = PostgresEvidenceRepository(pool)
        service = EvidenceService(repo)
        integrity = await run_replay_integrity(service)
        await close_pool(pool)
        print('\n--- Replay & Chain Integrity ---')
        for k, v in integrity.items():
            print(f'  {k}: {v}')
    else:
        print('\n(Set VRL_DATABASE_URL to also run the PostgreSQL benchmark.)\n')

    # --- write report ---
    full_report = {'runs': reports}
    REPORT_PATH.write_text(json.dumps(full_report, indent=2))
    print(f'\nReport written to: {REPORT_PATH}')

    # --- exit code ---
    pg_runs = [r for r in reports if r['label'] == 'postgresql']
    if pg_runs:
        pg = pg_runs[0]
        if not pg['targets']['p95_lt_100ms']:
            print('\nFAIL: p95 latency exceeds 100ms target')
            sys.exit(1)
        if not pg['targets']['audit_chain_valid']:
            print('\nFAIL: audit chain is not valid')
            sys.exit(1)
    print('\nAll assertions passed.')


def _print_report(r: dict) -> None:
    lm = r['latency_ms']
    tgt = r['targets']
    print(f"\n  [{r['label']}]")
    print(f"  Concurrency: {r['concurrency']} ({r['unique_inputs']} unique, {r['duplicate_inputs']} dup)")
    print(f"  Wall time:   {r['total_wall_ms']} ms   Throughput: {r['throughput_rps']} req/s")
    print(f"  Latency:     p50={lm['p50']}ms  p95={lm['p95']}ms  p99={lm['p99']}ms  max={lm['max']}ms")
    print(f"  Status:      {r['status_counts']}")
    print(f"  Audit chain: {r['audit_chain']['status']}  ({r['audit_chain']['checked_rows']} rows)")
    print(f"  p95 < 100ms: {pass_fail(tgt['p95_lt_100ms'])}   "
          f"p95 < 50ms: {pass_fail(tgt['p95_lt_50ms'])}   "
          f"chain valid: {pass_fail(tgt['audit_chain_valid'])}")


if __name__ == '__main__':
    asyncio.run(main())
