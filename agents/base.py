"""
agents/base.py
==============
Foundation types for the 10-agent ZK Engineering Unit.

All agents implement BaseAgent. Tasks flow through the Coordinator,
which dispatches them, collects TaskResults, and updates SharedMemory.

Design constraints
------------------
- Agents are stateless by default; state is in SharedMemory.
- Every run() call is deterministic given the same Task and memory snapshot.
- performance_score is maintained by the Coordinator via PerformanceTracker;
  agents never update their own score.
"""
from __future__ import annotations

import abc
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from zk.interfaces import ArtifactType, DeterministicArtifact


class AgentStatus(str, Enum):
    IDLE = 'idle'
    RUNNING = 'running'
    DONE = 'done'
    FAILED = 'failed'
    REPLACED = 'replaced'


class TaskPriority(int, Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class TaskDomain(str, Enum):
    ARCHITECTURE = 'architecture'
    CIRCUIT = 'circuit'
    BACKEND = 'backend'
    VERIFICATION = 'verification'
    PERFORMANCE = 'performance'
    SECURITY = 'security'
    DATA_INTEGRITY = 'data_integrity'
    DEVOPS = 'devops'
    TESTING = 'testing'
    RESEARCH = 'research'
    COORDINATION = 'coordination'


@dataclass
class Task:
    task_id: str
    domain: TaskDomain
    description: str
    inputs: dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    cycle: int = 0
    depends_on: list[str] = field(default_factory=list)
    strategy_key: str = ''
    consumes: list[ArtifactType] = field(default_factory=list)
    produces: list[ArtifactType] = field(default_factory=list)
    max_execution_ms: float | None = None
    max_artifact_bytes: int | None = None
    max_circuit_constraints: int | None = None
    created_at: float = field(default_factory=time.time)


@dataclass
class TaskResult:
    task_id: str
    agent_id: str
    status: str
    outputs: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, str] = field(default_factory=dict)
    produced_artifacts: list[DeterministicArtifact] = field(default_factory=list)
    consumed_artifact_ids: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    constraint_violations: list[str] = field(default_factory=list)
    duration_ms: float = 0.0
    memory_entries: list[dict[str, Any]] = field(default_factory=list)
    completed_at: float = field(default_factory=time.time)


class BaseAgent(abc.ABC):
    agent_id: str
    domain: TaskDomain
    version: str = '1.0.0'
    performance_score: float = 1.0
    status: AgentStatus = AgentStatus.IDLE

    @abc.abstractmethod
    def run(self, task: 'Task', memory: 'Any') -> 'TaskResult':
        """Execute the task and return a deterministic result."""

    def accepts(self, task: 'Task') -> bool:
        return task.domain == self.domain

    def describe(self) -> str:
        return f'[{self.agent_id} v{self.version}] domain={self.domain.value}'

    def _make_result(
        self,
        task: 'Task',
        *,
        status: str = 'success',
        outputs: dict[str, Any] | None = None,
        errors: list[str] | None = None,
        memory_entries: list[dict[str, Any]] | None = None,
        produced_artifacts: list[DeterministicArtifact] | None = None,
        consumed_artifact_ids: list[str] | None = None,
        constraint_violations: list[str] | None = None,
        start_time: float | None = None,
    ) -> 'TaskResult':
        return TaskResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            status=status,
            outputs=outputs or {},
            errors=errors or [],
            memory_entries=memory_entries or [],
            produced_artifacts=produced_artifacts or [],
            consumed_artifact_ids=consumed_artifact_ids or [],
            constraint_violations=constraint_violations or [],
            duration_ms=(time.perf_counter() - start_time) * 1000 if start_time else 0.0,
        )
