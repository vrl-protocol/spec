"""Async proof queue for the verified Halo2 path.

The queue is append-only at the event level: each state transition is stored as
a new immutable snapshot and mirrored to JSONL for forensic replay.
"""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from time import monotonic, time
from typing import Literal

from utils.canonical import canonical_json
from utils.hashing import sha256_hex
from zk.compiler.plonk_adapter import compile_circuit
from zk.interfaces import Proof, VerificationResult, Witness

_QUEUE_LOG = Path(__file__).resolve().parents[1] / 'logs' / 'proof_queue.jsonl'


@dataclass(frozen=True)
class ProofTask:
  task_id: str
  witness_artifact_id: str
  circuit_artifact_id: str
  trace_hash: str
  input_hash: str
  created_at: float
  status: Literal['pending', 'processing', 'completed', 'failed'] = 'pending'
  result: Proof | None = None
  verification: VerificationResult | None = None
  error: str | None = None
  elapsed_ms: float | None = None


class ProofQueue:
  def __init__(self, max_workers: int = 1) -> None:
    self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix='plonk-prover')
    self._events: list[ProofTask] = []
    self._lock = threading.Lock()

  def _append_event(self, task: ProofTask) -> None:
    with self._lock:
      self._events.append(task)
    _QUEUE_LOG.parent.mkdir(parents=True, exist_ok=True)
    serializable = asdict(task)
    if task.result is not None:
      serializable['result'] = task.result.model_dump(mode='python')
    if task.verification is not None:
      serializable['verification'] = task.verification.model_dump(mode='python')
    # canonical_json rejects floats; convert timestamps to strings
    if isinstance(serializable.get('created_at'), float):
      serializable['created_at'] = str(serializable['created_at'])
    if isinstance(serializable.get('elapsed_ms'), float):
      serializable['elapsed_ms'] = str(serializable['elapsed_ms'])
    with _QUEUE_LOG.open('a', encoding='utf-8', newline='\n') as handle:
      handle.write(canonical_json(serializable) + '\n')

  def _latest_for(self, task_id: str) -> ProofTask | None:
    for task in reversed(self._events):
      if task.task_id == task_id:
        return task
    return None

  def submit(self, witness_artifact: Witness, trace_hash: str, *, produced_by: str = 'proof_queue', cycle: int = 1, auto_verify: bool = True) -> str:
    circuit = compile_circuit()
    task_id = 'proofjob_' + sha256_hex(
      canonical_json(
        {
          'witness_artifact_id': witness_artifact.artifact_id,
          'trace_hash': trace_hash,
          'produced_by': produced_by,
          'cycle': cycle,
          'circuit_hash': circuit.circuit_hash,
        }
      )
    )[:24]
    existing = self._latest_for(task_id)
    if existing is not None and existing.status in {'pending', 'processing', 'completed'}:
      return task_id

    task = ProofTask(
      task_id=task_id,
      witness_artifact_id=witness_artifact.artifact_id,
      circuit_artifact_id=f'circuit_{circuit.circuit_hash[:24]}',
      trace_hash=trace_hash,
      input_hash=witness_artifact.input_hash,
      created_at=time(),
      status='pending',
    )
    self._append_event(task)
    self._executor.submit(self._run_task, task, witness_artifact, produced_by, cycle, auto_verify)
    return task_id

  def _run_task(self, pending_task: ProofTask, witness_artifact: Witness, produced_by: str, cycle: int, auto_verify: bool) -> None:
    processing_task = ProofTask(
      task_id=pending_task.task_id,
      witness_artifact_id=pending_task.witness_artifact_id,
      circuit_artifact_id=pending_task.circuit_artifact_id,
      trace_hash=pending_task.trace_hash,
      input_hash=pending_task.input_hash,
      created_at=pending_task.created_at,
      status='processing',
    )
    self._append_event(processing_task)

    start = monotonic()
    try:
      from zk.provers.plonk_prover import build_plonk_proof
      from zk.verifiers.plonk_verifier import verify_plonk_proof

      proof = build_plonk_proof(
        witness_artifact,
        pending_task.trace_hash,
        produced_by=produced_by,
        cycle=cycle,
      )
      verification: VerificationResult | None = None
      if auto_verify:
        verification = verify_plonk_proof(
          proof,
          produced_by=f'{produced_by}_verifier',
          cycle=cycle,
        )
      elapsed = round((monotonic() - start) * 1000, 1)
      completed_task = ProofTask(
        task_id=pending_task.task_id,
        witness_artifact_id=pending_task.witness_artifact_id,
        circuit_artifact_id=pending_task.circuit_artifact_id,
        trace_hash=pending_task.trace_hash,
        input_hash=pending_task.input_hash,
        created_at=pending_task.created_at,
        status='completed',
        result=proof,
        verification=verification,
        elapsed_ms=elapsed,
      )
      self._append_event(completed_task)
    except Exception as exc:
      elapsed = round((monotonic() - start) * 1000, 1)
      failed_task = ProofTask(
        task_id=pending_task.task_id,
        witness_artifact_id=pending_task.witness_artifact_id,
        circuit_artifact_id=pending_task.circuit_artifact_id,
        trace_hash=pending_task.trace_hash,
        input_hash=pending_task.input_hash,
        created_at=pending_task.created_at,
        status='failed',
        error=str(exc),
        elapsed_ms=elapsed,
      )
      self._append_event(failed_task)

  def get_task(self, task_id: str) -> ProofTask | None:
    with self._lock:
      for task in reversed(self._events):
        if task.task_id == task_id:
          return task
    return None

  def snapshot(self) -> dict[str, int]:
    with self._lock:
      latest: dict[str, ProofTask] = {}
      for task in self._events:
        latest[task.task_id] = task
    tasks = list(latest.values())
    return {
      'total': len(tasks),
      'pending': sum(1 for task in tasks if task.status == 'pending'),
      'processing': sum(1 for task in tasks if task.status == 'processing'),
      'completed': sum(1 for task in tasks if task.status == 'completed'),
      'failed': sum(1 for task in tasks if task.status == 'failed'),
    }

  def shutdown(self, wait: bool = True) -> None:
    self._executor.shutdown(wait=wait)


proof_queue = ProofQueue(max_workers=1)
