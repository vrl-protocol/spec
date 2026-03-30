from __future__ import annotations

import asyncio
import json
import os
import statistics
import subprocess  # nosec B404
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request

import asyncpg

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.connection import DatabaseSettings, close_pool, create_pool  # noqa: E402
from app.db.repository import PostgresEvidenceRepository  # noqa: E402
from app.services.evidence_service import EvidenceService  # noqa: E402
from core.engine import calculate_import_landed_cost  # noqa: E402
from core.sample import REFERENCE_REQUEST  # noqa: E402
from models.schemas import ImportCalculationRequest  # noqa: E402

PG_BIN = Path(r"C:\Program Files\PostgreSQL\17\bin")
PSQL = PG_BIN / "psql.exe"
CREATEDB = PG_BIN / "createdb.exe"
HOST = "127.0.0.1"
PORT = 5432
API_PORT = 8010
DB_NAME = "vrl_live_validation"
SUPERUSER = "postgres"
SUPERUSER_PASSWORD = os.getenv("VRL_SUPERUSER_PASSWORD", "postgres")
WRITER_USER = "vrl_writer"
WRITER_PASSWORD = os.getenv("VRL_WRITER_PASSWORD", "vrl_writer_local_2026!")
READER_USER = "vrl_reader"
READER_PASSWORD = os.getenv("VRL_READER_PASSWORD", "vrl_reader_local_2026!")
REPORT_DIR = ROOT / "docs" / "live-validation"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
API_LOG = REPORT_DIR / "api-server.log"
MIGRATION = ROOT / "migrations" / "001_init.sql"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = max(0, min(len(ordered) - 1, round((p / 100) * (len(ordered) - 1))))
    return ordered[index]


def database_url(user: str, password: str, db_name: str = DB_NAME) -> str:
    return f"postgresql://{user}:{parse.quote(password, safe='')}@{HOST}:{PORT}/{db_name}"


def asyncpg_connect_kwargs(user: str, password: str, db_name: str = DB_NAME) -> dict[str, Any]:
    return {
        "user": user,
        "password": password,
        "host": HOST,
        "port": PORT,
        "database": db_name,
        "ssl": False,
        "timeout": 5,
    }


async def open_connection(user: str, password: str, db_name: str = DB_NAME) -> asyncpg.Connection:
    conn = await asyncpg.connect(**asyncpg_connect_kwargs(user, password, db_name))
    await conn.set_type_codec(
        'jsonb',
        schema='pg_catalog',
        encoder=lambda value: json.dumps(value),
        decoder=json.loads,
        format='text',
    )
    return conn


def api_env() -> dict[str, str]:
    env = os.environ.copy()
    env["VRL_DATABASE_URL"] = database_url(WRITER_USER, WRITER_PASSWORD)
    env["VRL_DB_REQUIRE_TLS"] = "false"
    env["VRL_API_RATE_LIMIT"] = "1000"
    env["VRL_API_RATE_LIMIT_WINDOW_SECONDS"] = "60"
    return env


def run_subprocess(args: list[str], *, env: dict[str, str] | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(  # nosec B603
        args,
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(args)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
    return result


def psql(sql: str, *, db: str = "postgres", user: str = SUPERUSER, password: str = SUPERUSER_PASSWORD, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PGPASSWORD"] = password
    return run_subprocess(
        [
            str(PSQL),
            "-h",
            HOST,
            "-p",
            str(PORT),
            "-U",
            user,
            "-d",
            db,
            "-w",
            "-v",
            "ON_ERROR_STOP=1",
            "-t",
            "-A",
            "-c",
            sql,
        ],
        env=env,
        check=check,
    )


def provision_database() -> dict[str, Any]:
    psql(f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{DB_NAME}' AND pid <> pg_backend_pid();")  # nosec B608
    psql(f"DROP DATABASE IF EXISTS {DB_NAME};")  # nosec B608
    env = os.environ.copy()
    env["PGPASSWORD"] = SUPERUSER_PASSWORD
    run_subprocess([
        str(CREATEDB), "-h", HOST, "-p", str(PORT), "-U", SUPERUSER, "-w", DB_NAME,
    ], env=env)
    run_subprocess([
        str(PSQL), "-h", HOST, "-p", str(PORT), "-U", SUPERUSER, "-d", DB_NAME, "-w", "-v", "ON_ERROR_STOP=1", "-f", str(MIGRATION),
    ], env=env)
    psql(
        f"ALTER ROLE {WRITER_USER} WITH PASSWORD '{WRITER_PASSWORD}'; "
        f"ALTER ROLE {READER_USER} WITH PASSWORD '{READER_PASSWORD}';",
        db=DB_NAME,
    )
    settings = psql(
        "SELECT current_setting('server_version'), current_setting('wal_level'), current_setting('synchronous_commit'), current_setting('ssl');"
    ).stdout.strip().split("|")
    return {
        "database": DB_NAME,
        "server_version": settings[0],
        "wal_level": settings[1],
        "synchronous_commit": settings[2],
        "ssl": settings[3],
        "migration": str(MIGRATION),
        "status": "PASS",
    }


def base_payload() -> dict[str, Any]:
    return {
        "hs_code": REFERENCE_REQUEST["hs_code"],
        "country_of_origin": REFERENCE_REQUEST["country_of_origin"],
        "customs_value": str(REFERENCE_REQUEST["customs_value"]),
        "freight": str(REFERENCE_REQUEST["freight"]),
        "insurance": str(REFERENCE_REQUEST["insurance"]),
        "quantity": REFERENCE_REQUEST["quantity"],
        "shipping_mode": REFERENCE_REQUEST["shipping_mode"],
    }


def unique_payload(index: int) -> dict[str, Any]:
    payload = base_payload()
    payload["customs_value"] = f"{1200 + index}.00"
    payload["freight"] = f"{50 + (index % 25)}.00"
    payload["insurance"] = f"{10 + (index % 5)}.00"
    payload["quantity"] = 1 + (index % 7)
    return payload


def http_post_json(path: str, payload: Any, *, raw: bool = False, timeout_seconds: int = 30) -> dict[str, Any]:
    started = time.perf_counter()
    if raw:
        body = payload if isinstance(payload, bytes) else str(payload).encode("utf-8")
    else:
        body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        f"http://{HOST}:{API_PORT}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:  # nosec B310
            response_body = response.read().decode("utf-8")
            status = response.status
    except error.HTTPError as exc:
        response_body = exc.read().decode("utf-8")
        status = exc.code
    except Exception as exc:  # pragma: no cover - diagnostic surface
        return {
            "status": 0,
            "error": str(exc),
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        }
    try:
        parsed = json.loads(response_body) if response_body else None
    except json.JSONDecodeError:
        parsed = response_body
    return {
        "status": status,
        "body": parsed,
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
    }


def start_api() -> tuple[subprocess.Popen[str], Any]:
    log_handle = API_LOG.open("a", encoding="utf-8")
    process = subprocess.Popen(  # nosec B603
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", HOST, "--port", str(API_PORT)],
        cwd=str(ROOT),
        env=api_env(),
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        text=True,
    )
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            with request.urlopen(f"http://{HOST}:{API_PORT}/healthz", timeout=1) as response:  # nosec B310
                body = json.loads(response.read().decode("utf-8"))
                if response.status == 200 and body.get("database_configured"):
                    return process, log_handle
        except Exception:
            time.sleep(0.5)
    process.terminate()
    log_handle.close()
    raise RuntimeError("API server failed to start within the timeout window")


def stop_api(process: subprocess.Popen[str] | None, log_handle: Any | None) -> None:
    if process is not None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
    if log_handle is not None:
        log_handle.close()


async def build_service() -> tuple[Any, PostgresEvidenceRepository, EvidenceService]:
    settings = DatabaseSettings(url=database_url(WRITER_USER, WRITER_PASSWORD), require_tls=False)
    pool = await create_pool(settings)
    repository = PostgresEvidenceRepository(
        pool,
        statement_timeout_ms=settings.statement_timeout_ms,
        lock_timeout_ms=settings.lock_timeout_ms,
        connect_timeout_seconds=settings.connect_timeout_seconds,
    )
    service = EvidenceService(repository)
    return pool, repository, service


async def query_value(sql: str, *args: Any) -> Any:
    conn = await open_connection(WRITER_USER, WRITER_PASSWORD)
    try:
        return await conn.fetchval(sql, *args)
    finally:
        await conn.close()


async def query_row(sql: str, *args: Any, superuser: bool = False) -> asyncpg.Record | None:
    conn = await open_connection(SUPERUSER, SUPERUSER_PASSWORD) if superuser else await open_connection(WRITER_USER, WRITER_PASSWORD)
    try:
        return await conn.fetchrow(sql, *args)
    finally:
        await conn.close()


async def query_rows(sql: str, *args: Any, superuser: bool = False) -> list[asyncpg.Record]:
    conn = await open_connection(SUPERUSER, SUPERUSER_PASSWORD) if superuser else await open_connection(WRITER_USER, WRITER_PASSWORD)
    try:
        return await conn.fetch(sql, *args)
    finally:
        await conn.close()


async def step_immutability() -> dict[str, Any]:
    pool, repository, service = await build_service()
    try:
        seeded = await service.calculate_and_persist(base_payload())
        writer_update_error = None
        writer_delete_error = None
        superuser_update_error = None
        writer_conn = await asyncpg.connect(**asyncpg_connect_kwargs(WRITER_USER, WRITER_PASSWORD))
        try:
            try:
                await writer_conn.execute("UPDATE requests SET input_hash = 'tamper'")
            except Exception as exc:
                writer_update_error = str(exc)
            try:
                await writer_conn.execute("DELETE FROM results")
            except Exception as exc:
                writer_delete_error = str(exc)
        finally:
            await writer_conn.close()

        super_conn = await asyncpg.connect(**asyncpg_connect_kwargs(SUPERUSER, SUPERUSER_PASSWORD))
        try:
            try:
                await super_conn.execute("UPDATE requests SET input_hash = 'tamper' WHERE id = $1", seeded.evidence.request.id)
            except Exception as exc:
                superuser_update_error = str(exc)
        finally:
            await super_conn.close()

        counts = await query_row(
            "SELECT (SELECT count(*) FROM requests) AS requests, (SELECT count(*) FROM results) AS results, (SELECT count(*) FROM proofs) AS proofs, (SELECT count(*) FROM audit_log) AS audit_log"
        )
        passed = all([
            writer_update_error is not None,
            writer_delete_error is not None,
            superuser_update_error is not None,
        ])
        return {
            "step": "immutability_test",
            "status": "PASS" if passed else "FAIL",
            "seed_input_hash": seeded.proof.input_hash,
            "seed_output_hash": seeded.proof.output_hash,
            "seed_final_proof": seeded.proof.final_proof,
            "writer_update_error": writer_update_error,
            "writer_delete_error": writer_delete_error,
            "superuser_update_error": superuser_update_error,
            "row_counts": dict(counts) if counts is not None else {},
        }
    finally:
        await close_pool(pool)


def verify_audit_chain_script() -> dict[str, Any]:
    env = api_env()
    env["VRL_DATABASE_URL"] = database_url(READER_USER, READER_PASSWORD)
    result = run_subprocess([sys.executable, "scripts/verify_audit_chain.py"], env=env, check=False)
    payload = json.loads(result.stdout)
    payload["exit_code"] = result.returncode
    return payload


async def step_live_api_duplicate() -> dict[str, Any]:
    first = http_post_json("/calculate", base_payload())
    second = http_post_json("/calculate", base_payload())
    audit_rows = await query_rows("SELECT id, event_type, reference_id::text AS reference_id, prev_hash, current_hash, event_payload FROM audit_log ORDER BY id")
    duplicate_logged = any(row["event_type"] == "calculation_rejected_duplicate" for row in audit_rows)
    return {
        "step": "live_api_duplicate",
        "status": "PASS" if first["status"] == 200 and second["status"] == 409 and duplicate_logged else "FAIL",
        "first_request": first,
        "second_request": second,
        "audit_rows": [dict(row) for row in audit_rows],
    }


async def step_audit_chain_validation() -> dict[str, Any]:
    pre = verify_audit_chain_script()
    normal_tamper_error = None
    super_conn = await asyncpg.connect(**asyncpg_connect_kwargs(SUPERUSER, SUPERUSER_PASSWORD))
    try:
        try:
            await super_conn.execute("UPDATE audit_log SET current_hash = 'fake' WHERE id = (SELECT min(id) FROM audit_log)")
        except Exception as exc:
            normal_tamper_error = str(exc)
        await super_conn.execute("SET session_replication_role = replica")
        await super_conn.execute("UPDATE audit_log SET current_hash = 'fake' WHERE id = (SELECT min(id) FROM audit_log)")
        await super_conn.execute("SET session_replication_role = DEFAULT")
    finally:
        await super_conn.close()
    post = verify_audit_chain_script()
    return {
        "step": "audit_chain_validation",
        "status": "PASS" if pre["status"] == "VALID" and post["status"] == "INVALID" and normal_tamper_error is not None else "FAIL",
        "pre_tamper": pre,
        "normal_tamper_error": normal_tamper_error,
        "post_tamper": post,
    }


class ProfilingSession:
    def __init__(self, inner_context: Any, metrics: list[dict[str, float]]) -> None:
        self._inner_context = inner_context
        self._metrics = metrics
        self._inner = None
        self._started = 0.0
        self._lock_wait_ms = 0.0

    async def __aenter__(self) -> "ProfilingSession":
        self._started = time.perf_counter()
        self._inner = await self._inner_context.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        try:
            await self._inner_context.__aexit__(exc_type, exc, tb)
        finally:
            self._metrics.append(
                {
                    "tx_ms": round((time.perf_counter() - self._started) * 1000, 2),
                    "lock_wait_ms": round(self._lock_wait_ms, 2),
                }
            )

    async def acquire_audit_chain_lock(self) -> None:
        if self._inner is None:
            raise RuntimeError("ProfilingSession is not active")
        started = time.perf_counter()
        await self._inner.acquire_audit_chain_lock()
        self._lock_wait_ms = (time.perf_counter() - started) * 1000

    def __getattr__(self, item: str) -> Any:
        if self._inner is None:
            raise AttributeError(item)
        return getattr(self._inner, item)


class ProfilingRepository:
    def __init__(self, inner: PostgresEvidenceRepository, metrics: list[dict[str, float]]) -> None:
        self._inner = inner
        self._metrics = metrics

    def transaction(self, *, read_only: bool = False) -> ProfilingSession:
        return ProfilingSession(self._inner.transaction(read_only=read_only), self._metrics)

    async def fetch_by_input_hash(self, input_hash: str):
        return await self._inner.fetch_by_input_hash(input_hash)

    async def fetch_audit_chain(self):
        return await self._inner.fetch_audit_chain()


async def step_concurrency_and_latency() -> tuple[dict[str, Any], dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for index in range(100):
        if index < 30:
            payloads.append(base_payload())
        else:
            payloads.append(unique_payload(index))

    def submit(index: int, payload: dict[str, Any]) -> dict[str, Any]:
        result = http_post_json("/calculate", payload, timeout_seconds=60)
        result["index"] = index
        if isinstance(result.get("body"), dict):
            proof = result["body"].get("proof") or {}
            result["input_hash"] = proof.get("input_hash")
            result["output_hash"] = proof.get("output_hash")
            result["final_proof"] = proof.get("final_proof")
        return result

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=25) as executor:
        futures = [executor.submit(submit, index, payload) for index, payload in enumerate(payloads)]
        results = [future.result() for future in as_completed(futures)]
    total_elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    results.sort(key=lambda item: item["index"])

    status_counts: dict[str, int] = {}
    for item in results:
        key = str(item["status"])
        status_counts[key] = status_counts.get(key, 0) + 1

    chain = verify_audit_chain_script()
    hash_counts = await query_row("SELECT COUNT(*) AS total, COUNT(DISTINCT current_hash) AS unique_hashes FROM audit_log")
    concurrency_report = {
        "step": "concurrency_stress",
        "status": "PASS" if status_counts.get("200", 0) == 71 and status_counts.get("409", 0) == 29 and chain["status"] == "VALID" and hash_counts["total"] == hash_counts["unique_hashes"] else "FAIL",
        "total_elapsed_ms": total_elapsed_ms,
        "status_counts": status_counts,
        "responses": results,
        "audit_chain": chain,
        "hash_counts": dict(hash_counts),
        "deadlock_detected": any(item["status"] == 500 or item["status"] == 0 for item in results),
    }

    metrics: list[dict[str, float]] = []
    pool, repository, _ = await build_service()
    profiling_service = EvidenceService(ProfilingRepository(repository, metrics))
    try:
        await asyncio.gather(*[profiling_service.calculate_and_persist(unique_payload(200 + index)) for index in range(10)])
    finally:
        await close_pool(pool)
    request_latencies = [item["latency_ms"] for item in results if item["status"] in {200, 409}]
    tx_latencies = [metric["tx_ms"] for metric in metrics]
    lock_waits = [metric["lock_wait_ms"] for metric in metrics]
    latency_report = {
        "step": "latency_measurement",
        "status": "PASS" if percentile(request_latencies, 95) < 100 else "WARN",
        "total_request_latency_ms": {
            "p50": percentile(request_latencies, 50),
            "p95": percentile(request_latencies, 95),
            "max": max(request_latencies) if request_latencies else 0.0,
            "average": round(statistics.mean(request_latencies), 2) if request_latencies else 0.0,
        },
        "db_transaction_ms": {
            "p50": percentile(tx_latencies, 50),
            "p95": percentile(tx_latencies, 95),
            "max": max(tx_latencies) if tx_latencies else 0.0,
            "average": round(statistics.mean(tx_latencies), 2) if tx_latencies else 0.0,
        },
        "lock_wait_ms": {
            "p50": percentile(lock_waits, 50),
            "p95": percentile(lock_waits, 95),
            "max": max(lock_waits) if lock_waits else 0.0,
            "average": round(statistics.mean(lock_waits), 2) if lock_waits else 0.0,
        },
        "note": "P95 request latency over 100ms indicates the audit-chain serialization lock is the likely bottleneck." if percentile(request_latencies, 95) >= 100 else "Latency stayed within the 100ms acceptable envelope.",
    }
    return concurrency_report, latency_report


async def step_replay_validation() -> dict[str, Any]:
    row = await query_row(
        "SELECT r.raw_input, s.raw_output, r.input_hash, s.output_hash, p.final_proof FROM requests r JOIN results s ON s.request_id = r.id JOIN proofs p ON p.request_id = r.id ORDER BY r.created_at ASC LIMIT 1"
    )
    pool, _, service = await build_service()
    try:
        verification = await service.verify_persisted(row["raw_input"])
    finally:
        await close_pool(pool)
    recomputed = calculate_import_landed_cost(ImportCalculationRequest.model_validate(row["raw_input"]))
    passed = (
        verification.verification.status == "VALID"
        and row["input_hash"] == recomputed.proof.input_hash
        and row["output_hash"] == recomputed.proof.output_hash
        and row["final_proof"] == recomputed.proof.final_proof
    )
    return {
        "step": "replay_validation",
        "status": "PASS" if passed else "FAIL",
        "stored_input_hash": row["input_hash"],
        "stored_output_hash": row["output_hash"],
        "stored_final_proof": row["final_proof"],
        "recomputed_input_hash": recomputed.proof.input_hash,
        "recomputed_output_hash": recomputed.proof.output_hash,
        "recomputed_final_proof": recomputed.proof.final_proof,
        "verification": verification.model_dump(mode="json"),
    }


async def run_failure_worker(mode: str, marker_path: Path, input_hash: str) -> int:
    conn = await asyncpg.connect(**asyncpg_connect_kwargs(WRITER_USER, WRITER_PASSWORD))
    tx = conn.transaction()
    await tx.start()
    try:
        await conn.execute(
            "INSERT INTO requests (id, input_hash, raw_input, created_at) VALUES ($1, $2, $3::jsonb, $4)",
            __import__('uuid').uuid4(),
            input_hash,
            json.dumps({'mode': mode, 'input_hash': input_hash}),
            datetime.now(timezone.utc),
        )
        if mode == 'drop_connection':
            pid = await conn.fetchval('SELECT pg_backend_pid()')
            marker_path.write_text(json.dumps({'input_hash': input_hash, 'pid': pid}), encoding='utf-8')
        else:
            marker_path.write_text(json.dumps({'input_hash': input_hash}), encoding='utf-8')
        await asyncio.sleep(30)
        return 0
    finally:
        await conn.close()


async def step_failure_injection() -> dict[str, Any]:
    kill_marker = REPORT_DIR / "kill-mid-transaction.json"
    drop_marker = REPORT_DIR / "drop-connection.json"
    if kill_marker.exists():
        kill_marker.unlink()
    if drop_marker.exists():
        drop_marker.unlink()

    kill_hash = f"kill-mid-{int(time.time())}"
    kill_process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--failure-worker", "kill_process", str(kill_marker), kill_hash], cwd=str(ROOT), env=api_env())  # nosec B603
    deadline = time.time() + 10
    while time.time() < deadline and not kill_marker.exists():
        time.sleep(0.2)
    kill_process.kill()
    kill_process.wait(timeout=10)
    kill_count = await query_value("SELECT count(*) FROM requests WHERE input_hash = $1", kill_hash)

    drop_hash = f"drop-conn-{int(time.time())}"
    drop_process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--failure-worker", "drop_connection", str(drop_marker), drop_hash], cwd=str(ROOT), env=api_env())  # nosec B603
    deadline = time.time() + 10
    while time.time() < deadline and not drop_marker.exists():
        time.sleep(0.2)
    marker = json.loads(drop_marker.read_text(encoding="utf-8"))
    super_conn = await asyncpg.connect(**asyncpg_connect_kwargs(SUPERUSER, SUPERUSER_PASSWORD))
    try:
        await super_conn.execute(f"SELECT pg_terminate_backend({int(marker['pid'])})")
    finally:
        await super_conn.close()
    try:
        drop_process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        drop_process.kill()
        drop_process.wait(timeout=10)
    drop_count = await query_value("SELECT count(*) FROM requests WHERE input_hash = $1", drop_hash)

    duplicate_response = http_post_json("/calculate", base_payload())
    return {
        "step": "failure_injection",
        "status": "PASS" if kill_count == 0 and drop_count == 0 and duplicate_response["status"] == 409 else "FAIL",
        "kill_mid_transaction": {
            "input_hash": kill_hash,
            "residual_request_count": int(kill_count),
            "status": "PASS" if kill_count == 0 else "FAIL",
        },
        "drop_connection_mid_write": {
            "input_hash": drop_hash,
            "residual_request_count": int(drop_count),
            "terminated_backend_pid": marker["pid"],
            "status": "PASS" if drop_count == 0 else "FAIL",
        },
        "duplicate_hash_attempt": duplicate_response,
    }


async def step_adversarial_inputs() -> dict[str, Any]:
    before_audit = await query_value("SELECT count(*) FROM audit_log")
    injection_payload = base_payload()
    injection_payload["hs_code"] = "8507600000'; DROP TABLE requests;--"
    oversized_payload = {"padding": "A" * (2 * 1024 * 1024)}
    malformed_payload = b"[1,2,3]"
    invalid_hs_payload = base_payload()
    invalid_hs_payload["hs_code"] = "123"

    injection_result = http_post_json("/calculate", injection_payload)
    oversized_result = http_post_json("/calculate", oversized_payload)
    malformed_result = http_post_json("/calculate", malformed_payload, raw=True)
    invalid_hs_result = http_post_json("/calculate", invalid_hs_payload)
    after_audit = await query_value("SELECT count(*) FROM audit_log")

    passed = (
        injection_result["status"] == 400
        and oversized_result["status"] == 413
        and malformed_result["status"] == 400
        and invalid_hs_result["status"] == 400
        and before_audit == after_audit
    )
    return {
        "step": "adversarial_input_testing",
        "status": "PASS" if passed else "FAIL",
        "audit_log_count_before": int(before_audit),
        "audit_log_count_after": int(after_audit),
        "cases": {
            "sql_injection_payload": injection_result,
            "oversized_json": oversized_result,
            "malformed_schema": malformed_result,
            "invalid_hs_code": invalid_hs_result,
        },
    }


def write_report(name: str, payload: dict[str, Any]) -> None:
    (REPORT_DIR / name).write_text(json.dumps(payload, indent=2), encoding="utf-8")


async def main() -> int:
    summary: dict[str, Any] = {"started_at": now_iso()}
    summary["step_1"] = provision_database()
    summary["step_2"] = await step_immutability()

    provision_database()
    process = None
    log_handle = None
    try:
        process, log_handle = start_api()
        summary["step_3"] = await step_live_api_duplicate()
        summary["step_4"] = await step_audit_chain_validation()
    finally:
        stop_api(process, log_handle)

    provision_database()
    process = None
    log_handle = None
    try:
        process, log_handle = start_api()
        concurrency_report, latency_report = await step_concurrency_and_latency()
        summary["step_5"] = concurrency_report
        summary["step_6"] = latency_report
        summary["step_7"] = await step_replay_validation()
        summary["step_8"] = await step_failure_injection()
        summary["step_9"] = await step_adversarial_inputs()
    finally:
        stop_api(process, log_handle)

    summary["finished_at"] = now_iso()
    summary["step_10"] = {
        "status": "PASS" if all(summary[key]["status"] in {"PASS", "WARN"} for key in ["step_1", "step_2", "step_3", "step_4", "step_5", "step_6", "step_7", "step_8", "step_9"]) else "FAIL",
        "database_plus_proof_plus_replay": "identical truth" if summary["step_7"]["status"] == "PASS" else "divergent",
    }

    write_report("audit-chain-verification-report.json", {
        "generated_at": now_iso(),
        "step_3": summary["step_3"],
        "step_4": summary["step_4"],
    })
    write_report("concurrency-integrity-report.json", {
        "generated_at": now_iso(),
        "step_5": summary["step_5"],
        "step_7": summary["step_7"],
    })
    write_report("latency-report.json", {
        "generated_at": now_iso(),
        "step_6": summary["step_6"],
    })
    write_report("failure-test-report.json", {
        "generated_at": now_iso(),
        "step_8": summary["step_8"],
        "step_9": summary["step_9"],
    })
    write_report("summary.json", summary)

    print(json.dumps(summary, indent=2))
    return 0 if summary["step_10"]["status"] == "PASS" else 1


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == "--failure-worker":
        raise SystemExit(asyncio.run(run_failure_worker(sys.argv[2], Path(sys.argv[3]), sys.argv[4])))
    raise SystemExit(asyncio.run(main()))

