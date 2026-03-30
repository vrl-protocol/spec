from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from threading import Event, Lock, Thread
from typing import Any

from core.engine import calculate_import_landed_cost
from core.sample import REFERENCE_REQUEST
from core.tariffs import DATASET_HASH, DATASET_VERSION
from models.schemas import CalculationResponse, ImportCalculationRequest


@dataclass
class RuntimeSnapshot:
    started: bool = False
    iteration_count: int = 0
    last_run_at: str | None = None
    last_input_hash: str | None = None
    last_output_hash: str | None = None
    last_integrity_hash: str | None = None
    last_audit_hash: str | None = None
    last_status: str | None = None
    last_error: str | None = None
    last_result: dict[str, Any] | None = None
    last_trace: list[dict[str, Any]] | None = None


class RuntimeController:
    def __init__(self) -> None:
        self._lock = Lock()
        self._stop_event = Event()
        self._thread: Thread | None = None
        self._snapshot = RuntimeSnapshot()

    def record_response(self, response: CalculationResponse, *, audit_hash: str | None = None, status: str = 'ok') -> None:
        with self._lock:
            snapshot = self._snapshot
            snapshot.iteration_count += 1
            snapshot.last_run_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
            snapshot.last_input_hash = response.proof.input_hash
            snapshot.last_output_hash = response.proof.output_hash
            snapshot.last_integrity_hash = response.proof.integrity_hash
            snapshot.last_audit_hash = audit_hash
            snapshot.last_status = status
            snapshot.last_error = None
            snapshot.last_result = response.result.model_dump(mode='json')
            snapshot.last_trace = [step.model_dump(mode='json') for step in response.trace]

    def run_once(self, request_payload: object) -> CalculationResponse:
        request = ImportCalculationRequest.model_validate(request_payload)
        response = calculate_import_landed_cost(request)
        self.record_response(response, audit_hash=None, status='ephemeral')
        return response

    def start(self, interval_seconds: int = 30) -> RuntimeSnapshot:
        with self._lock:
            if self._thread and self._thread.is_alive():
                self._snapshot.started = True
                return self._snapshot
            self._stop_event.clear()
            self._snapshot.started = True
            self._thread = Thread(target=self._loop, args=(interval_seconds,), daemon=True)
            self._thread.start()
            return self._snapshot

    def stop(self) -> RuntimeSnapshot:
        with self._lock:
            self._stop_event.set()
            self._snapshot.started = False
            return self._snapshot

    def _loop(self, interval_seconds: int) -> None:
        while not self._stop_event.is_set():
            try:
                self.run_once(REFERENCE_REQUEST)
            except Exception as exc:  # pragma: no cover
                with self._lock:
                    self._snapshot.last_status = 'error'
                    self._snapshot.last_error = str(exc)
            self._stop_event.wait(interval_seconds)

    def dashboard(self) -> dict[str, Any]:
        with self._lock:
            snapshot = asdict(self._snapshot)
        return {
            'dataset_version': DATASET_VERSION,
            'dataset_hash': DATASET_HASH,
            'runtime': snapshot,
        }


runtime = RuntimeController()

