from __future__ import annotations

from dataclasses import dataclass, field

from agents.base import TaskResult

@dataclass
class AgentPerformance:
    agent_id: str
    score: float = 1.0
    consecutive_failures: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    avg_duration_ms: float = 0.0
    history: list[float] = field(default_factory=list)

class PerformanceTracker:
    def __init__(self) -> None:
        self._records: dict[str, AgentPerformance] = {}

    def record(self, result: TaskResult) -> AgentPerformance:
        record = self._records.setdefault(result.agent_id, AgentPerformance(agent_id=result.agent_id))
        success = result.status == 'success'
        record.tasks_completed += 1 if success else 0
        record.tasks_failed += 0 if success else 1
        record.consecutive_failures = 0 if success else record.consecutive_failures + 1
        record.history.append(result.duration_ms)
        record.avg_duration_ms = round(sum(record.history) / len(record.history), 2)
        success_component = 1.0 if success else 0.25
        duration_component = 1.0 / (1.0 + (result.duration_ms / 500.0))
        candidate_score = round((0.7 * success_component) + (0.3 * duration_component), 4)
        record.score = round((record.score * 0.6) + (candidate_score * 0.4), 4)
        return record

    def snapshot(self) -> dict[str, dict]:
        return {agent_id: {'score': record.score, 'consecutive_failures': record.consecutive_failures, 'tasks_completed': record.tasks_completed, 'tasks_failed': record.tasks_failed, 'avg_duration_ms': record.avg_duration_ms} for agent_id, record in sorted(self._records.items())}

    def underperformers(self, *, min_score: float = 0.45, min_failures: int = 2) -> list[str]:
        return [agent_id for agent_id, record in self._records.items() if record.score < min_score and record.consecutive_failures >= min_failures]
