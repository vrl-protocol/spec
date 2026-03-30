from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any

DEFAULT_MEMORY_DIR = Path(__file__).resolve().parent


@dataclass
class StrategyEntry:
    entry_id: str
    domain: str
    outcome: str
    pattern: str
    detail: str
    cycle: int
    agent_id: str
    timestamp: float = field(default_factory=time.time)
    tags: list[str] = field(default_factory=list)


@dataclass
class CircuitEntry:
    entry_id: str
    circuit_name: str
    constraint_count: int
    proving_system: str
    proving_time_ms: float
    description: str
    code_snippet: str
    cycle: int
    timestamp: float = field(default_factory=time.time)


@dataclass
class VulnerabilityEntry:
    entry_id: str
    name: str
    description: str
    severity: str
    mitigation: str
    affected_domains: list[str]
    cycle: int
    timestamp: float = field(default_factory=time.time)


@dataclass
class PerformanceEntry:
    entry_id: str
    agent_id: str
    cycle: int
    tasks_completed: int
    tasks_failed: int
    avg_duration_ms: float
    score: float
    timestamp: float = field(default_factory=time.time)


class SharedMemory:
    def __init__(self, base_dir: Path | str | None = None) -> None:
        self._lock = Lock()
        self._dir = Path(base_dir) if base_dir is not None else DEFAULT_MEMORY_DIR
        self._dir.mkdir(parents=True, exist_ok=True)
        self._strategy_file = self._dir / 'strategy_memory.json'
        self._circuit_file = self._dir / 'circuit_memory.json'
        self._vuln_file = self._dir / 'vulnerability_memory.json'
        self._performance_file = self._dir / 'performance_memory.json'
        self._strategy: list[dict[str, Any]] = []
        self._circuits: list[dict[str, Any]] = []
        self._vulns: list[dict[str, Any]] = []
        self._performance: list[dict[str, Any]] = []
        self._load_all()

    def _load_all(self) -> None:
        self._strategy = self._load(self._strategy_file)
        self._circuits = self._load(self._circuit_file)
        self._vulns = self._load(self._vuln_file)
        self._performance = self._load(self._performance_file)

    @staticmethod
    def _load(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            return []

    @staticmethod
    def _save(path: Path, data: list[dict[str, Any]]) -> None:
        tmp_fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix='.tmp', prefix=path.stem)
        try:
            with os.fdopen(tmp_fd, 'w', encoding='utf-8') as handle:
                json.dump(data, handle, indent=2, default=str)
            os.replace(tmp_path, path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def flush(self) -> None:
        with self._lock:
            self._save(self._strategy_file, self._strategy)
            self._save(self._circuit_file, self._circuits)
            self._save(self._vuln_file, self._vulns)
            self._save(self._performance_file, self._performance)

    def record_strategy(self, *, domain: str, outcome: str, pattern: str, detail: str, cycle: int, agent_id: str, tags: list[str] | None = None) -> str:
        entry_id = f"s_{int(time.time() * 1000)}_{len(self._strategy)}"
        entry = asdict(StrategyEntry(entry_id=entry_id, domain=domain, outcome=outcome, pattern=pattern, detail=detail, cycle=cycle, agent_id=agent_id, tags=tags or []))
        with self._lock:
            self._strategy.append(entry)
        return entry_id

    def record_circuit(self, *, circuit_name: str, constraint_count: int, proving_system: str, proving_time_ms: float, description: str, code_snippet: str, cycle: int) -> str:
        entry_id = f"c_{int(time.time() * 1000)}_{len(self._circuits)}"
        entry = asdict(CircuitEntry(entry_id=entry_id, circuit_name=circuit_name, constraint_count=constraint_count, proving_system=proving_system, proving_time_ms=proving_time_ms, description=description, code_snippet=code_snippet, cycle=cycle))
        with self._lock:
            self._circuits.append(entry)
        return entry_id

    def record_vulnerability(self, *, name: str, description: str, severity: str, mitigation: str, affected_domains: list[str], cycle: int) -> str:
        entry_id = f"v_{int(time.time() * 1000)}_{len(self._vulns)}"
        entry = asdict(VulnerabilityEntry(entry_id=entry_id, name=name, description=description, severity=severity, mitigation=mitigation, affected_domains=affected_domains, cycle=cycle))
        with self._lock:
            self._vulns.append(entry)
        return entry_id

    def record_performance(self, *, agent_id: str, cycle: int, tasks_completed: int, tasks_failed: int, avg_duration_ms: float, score: float) -> str:
        entry_id = f"p_{agent_id}_{cycle}"
        entry = asdict(PerformanceEntry(entry_id=entry_id, agent_id=agent_id, cycle=cycle, tasks_completed=tasks_completed, tasks_failed=tasks_failed, avg_duration_ms=avg_duration_ms, score=score))
        with self._lock:
            self._performance = [item for item in self._performance if not (item['agent_id'] == agent_id and item['cycle'] == cycle)]
            self._performance.append(entry)
        return entry_id

    def query_domain(self, domain: str) -> list[dict[str, Any]]:
        with self._lock:
            entries = [entry for entry in self._strategy if entry['domain'] == domain]
        return sorted(entries, key=lambda entry: (entry['cycle'], entry['timestamp'], entry['entry_id']), reverse=True)

    def query_failed_patterns(self, domain: str) -> list[str]:
        seen: list[str] = []
        for entry in self.query_domain(domain):
            if entry['outcome'] == 'failure' and entry['pattern'] not in seen:
                seen.append(entry['pattern'])
        return seen

    def latest_strategy(self, domain: str, pattern: str) -> dict[str, Any] | None:
        for entry in self.query_domain(domain):
            if entry['pattern'] == pattern:
                return entry
        return None

    def is_strategy_blocked(self, domain: str, pattern: str) -> bool:
        if not pattern:
            return False
        latest = self.latest_strategy(domain, pattern)
        return latest is not None and latest['outcome'] == 'failure'

    def preferred_patterns(self, domain: str, limit: int = 3) -> list[str]:
        scores: dict[str, dict[str, int]] = {}
        for entry in self.query_domain(domain):
            pattern = entry['pattern']
            if not pattern:
                continue
            bucket = scores.setdefault(pattern, {'success': 0, 'failure': 0})
            bucket['success' if entry['outcome'] == 'success' else 'failure'] += 1
        ranked = sorted(
            (
                (pattern, counts)
                for pattern, counts in scores.items()
                if counts['success'] > counts['failure']
            ),
            key=lambda item: (-item[1]['success'], item[1]['failure'], item[0]),
        )
        return [pattern for pattern, _ in ranked[:limit]]

    def control_decision(self, *, domain: str, pattern: str | None = None) -> dict[str, Any]:
        normalized_pattern = pattern or ''
        return {
            'blocked': self.is_strategy_blocked(domain, normalized_pattern),
            'pattern': normalized_pattern,
            'preferred_patterns': self.preferred_patterns(domain),
            'failed_patterns': self.query_failed_patterns(domain),
            'latest_entry': self.latest_strategy(domain, normalized_pattern) if normalized_pattern else None,
        }

    def query_circuits(self, proving_system: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            entries = list(self._circuits)
        if proving_system:
            entries = [entry for entry in entries if entry['proving_system'] == proving_system]
        return sorted(entries, key=lambda entry: (entry['constraint_count'], entry['circuit_name']))

    def get_vulnerabilities(self, severity: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            entries = list(self._vulns)
        if severity:
            entries = [entry for entry in entries if entry['severity'] == severity]
        return sorted(entries, key=lambda entry: (entry['cycle'], entry['timestamp'], entry['entry_id']), reverse=True)

    def get_agent_performance(self, agent_id: str) -> list[dict[str, Any]]:
        with self._lock:
            entries = [entry for entry in self._performance if entry['agent_id'] == agent_id]
        return sorted(entries, key=lambda entry: entry['cycle'])

    def apply_entries(self, entries: list[dict[str, Any]], cycle: int, agent_id: str) -> None:
        for entry in entries:
            entry_type = entry.get('type')
            if entry_type == 'strategy':
                self.record_strategy(
                    domain=entry.get('domain', 'unknown'),
                    outcome=entry.get('outcome', 'success'),
                    pattern=entry.get('pattern', ''),
                    detail=entry.get('detail', ''),
                    cycle=cycle,
                    agent_id=agent_id,
                    tags=entry.get('tags', []),
                )
            elif entry_type == 'circuit':
                self.record_circuit(
                    circuit_name=entry.get('circuit_name', 'unknown'),
                    constraint_count=entry.get('constraint_count', 0),
                    proving_system=entry.get('proving_system', 'stub'),
                    proving_time_ms=float(entry.get('proving_time_ms', 0.0)),
                    description=entry.get('description', ''),
                    code_snippet=entry.get('code_snippet', ''),
                    cycle=cycle,
                )
            elif entry_type == 'vulnerability':
                self.record_vulnerability(
                    name=entry.get('name', 'unknown'),
                    description=entry.get('description', ''),
                    severity=entry.get('severity', 'low'),
                    mitigation=entry.get('mitigation', ''),
                    affected_domains=entry.get('affected_domains', []),
                    cycle=cycle,
                )

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            strategy = list(self._strategy)
            circuits = list(self._circuits)
            vulns = list(self._vulns)
            perf = list(self._performance)
        domains = sorted({entry['domain'] for entry in strategy})
        failed_by_domain = {
            domain: len([entry for entry in strategy if entry['domain'] == domain and entry['outcome'] == 'failure'])
            for domain in domains
        }
        preferred_by_domain = {domain: self.preferred_patterns(domain) for domain in domains}
        return {
            'strategy_entries': len(strategy),
            'circuit_entries': len(circuits),
            'vulnerability_entries': len(vulns),
            'performance_entries': len(perf),
            'failed_patterns_by_domain': failed_by_domain,
            'preferred_patterns_by_domain': preferred_by_domain,
        }

    def summary(self) -> dict[str, Any]:
        return self.snapshot()
