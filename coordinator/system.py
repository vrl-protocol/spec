from __future__ import annotations

import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from agents.base import AgentStatus, BaseAgent, Task, TaskPriority, TaskDomain
from agents.zk_unit import build_agent_team
from coordinator.artifact_graph import ArtifactGraph
from coordinator.performance import PerformanceTracker
from infra.environment import build_environment_manifest
from memory.shared_memory import SharedMemory
from zk.interfaces import ArtifactType, DeterministicArtifact, artifact_size_bytes, summarize_artifact


@dataclass
class CycleExecution:
    cycle: int
    results: list[dict[str, Any]]
    replacements: list[dict[str, Any]]
    memory_summary: dict[str, Any]
    performance: dict[str, Any]
    artifact_graph: dict[str, Any]
    blocked_tasks: list[dict[str, Any]]
    log_path: str


class ZKCoordinator:
    def __init__(self, *, memory: SharedMemory | None = None, log_dir: Path | str | None = None, max_workers: int = 10) -> None:
        self.memory = memory or SharedMemory()
        self.log_dir = Path(log_dir) if log_dir is not None else Path(__file__).resolve().parents[1] / 'logs'
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.max_workers = max_workers
        self.performance = PerformanceTracker()
        self.agents = build_agent_team()
        self.last_artifact_graph: ArtifactGraph | None = None

    def build_initial_tasks(self, cycle: int = 1) -> list[Task]:
        prefix = f'cycle{cycle:02d}'
        return [
            Task(
                task_id=f'{prefix}_zk_architecture',
                domain=TaskDomain.ARCHITECTURE,
                description='Define the ZK proof system architecture and produce the initial circuit artifact.',
                priority=TaskPriority.CRITICAL,
                cycle=cycle,
                strategy_key='layered_proof_architecture',
                produces=[ArtifactType.CIRCUIT],
                max_execution_ms=750.0,
                max_artifact_bytes=32768,
                max_circuit_constraints=64,
            ),
            Task(
                task_id=f'{prefix}_circuit_design',
                domain=TaskDomain.CIRCUIT,
                description='Refine the circuit artifact for deterministic constraint execution.',
                priority=TaskPriority.CRITICAL,
                cycle=cycle,
                depends_on=[f'{prefix}_zk_architecture'],
                strategy_key='trace_to_constraints_mapping',
                consumes=[ArtifactType.CIRCUIT],
                produces=[ArtifactType.CIRCUIT],
                max_execution_ms=750.0,
                max_artifact_bytes=32768,
                max_circuit_constraints=64,
                inputs={'artifact_requirements': [{'artifact_type': ArtifactType.CIRCUIT.value, 'produced_by': 'zk_architect'}]},
            ),
            Task(
                task_id=f'{prefix}_backend_integration',
                domain=TaskDomain.BACKEND,
                description='Extract deterministic trace and witness artifacts from the VRL engine.',
                priority=TaskPriority.HIGH,
                cycle=cycle,
                depends_on=[f'{prefix}_circuit_design'],
                strategy_key='deterministic_trace_extraction',
                consumes=[ArtifactType.CIRCUIT],
                produces=[ArtifactType.TRACE, ArtifactType.WITNESS],
                max_execution_ms=1000.0,
                max_artifact_bytes=65536,
                inputs={'artifact_requirements': [{'artifact_type': ArtifactType.CIRCUIT.value, 'produced_by': 'circuit_engineer'}]},
            ),
            Task(
                task_id=f'{prefix}_prove_bundle',
                domain=TaskDomain.PERFORMANCE,
                description='Produce a structured deterministic proof artifact and benchmark the stub prover.',
                priority=TaskPriority.CRITICAL,
                cycle=cycle,
                depends_on=[f'{prefix}_backend_integration'],
                strategy_key='structured_stub_proof',
                consumes=[ArtifactType.CIRCUIT, ArtifactType.TRACE, ArtifactType.WITNESS],
                produces=[ArtifactType.PROOF],
                max_execution_ms=1000.0,
                max_artifact_bytes=32768,
                inputs={
                    'artifact_requirements': [
                        {'artifact_type': ArtifactType.CIRCUIT.value, 'produced_by': 'circuit_engineer'},
                        {'artifact_type': ArtifactType.TRACE.value, 'produced_by': 'backend_integration'},
                        {'artifact_type': ArtifactType.WITNESS.value, 'produced_by': 'backend_integration'},
                    ]
                },
            ),
            Task(
                task_id=f'{prefix}_verifier',
                domain=TaskDomain.VERIFICATION,
                description='Verify the structured proof artifact against its circuit, trace, and witness.',
                priority=TaskPriority.CRITICAL,
                cycle=cycle,
                depends_on=[f'{prefix}_prove_bundle'],
                strategy_key='structured_stub_verifier',
                consumes=[ArtifactType.CIRCUIT, ArtifactType.TRACE, ArtifactType.WITNESS, ArtifactType.PROOF],
                produces=[ArtifactType.VERIFICATION_RESULT],
                max_execution_ms=1000.0,
                max_artifact_bytes=32768,
                inputs={
                    'artifact_requirements': [
                        {'artifact_type': ArtifactType.CIRCUIT.value, 'produced_by': 'circuit_engineer'},
                        {'artifact_type': ArtifactType.TRACE.value, 'produced_by': 'backend_integration'},
                        {'artifact_type': ArtifactType.WITNESS.value, 'produced_by': 'backend_integration'},
                        {'artifact_type': ArtifactType.PROOF.value, 'produced_by': 'performance_optimization'},
                    ]
                },
            ),
            Task(
                task_id=f'{prefix}_testing',
                domain=TaskDomain.TESTING,
                description='Run deterministic pipeline smoke tests against the typed artifacts.',
                priority=TaskPriority.HIGH,
                cycle=cycle,
                depends_on=[f'{prefix}_verifier'],
                strategy_key='artifact_pipeline_smoke',
                consumes=[ArtifactType.PROOF, ArtifactType.VERIFICATION_RESULT],
                produces=[ArtifactType.VERIFICATION_RESULT],
                max_execution_ms=1200.0,
                max_artifact_bytes=32768,
                inputs={
                    'artifact_requirements': [
                        {'artifact_type': ArtifactType.PROOF.value, 'produced_by': 'performance_optimization'},
                        {'artifact_type': ArtifactType.VERIFICATION_RESULT.value, 'produced_by': 'verifier_agent'},
                    ]
                },
            ),
            Task(
                task_id=f'{prefix}_security',
                domain=TaskDomain.SECURITY,
                description='Inject malformed artifacts and ensure the pipeline rejects invalid states.',
                priority=TaskPriority.CRITICAL,
                cycle=cycle,
                depends_on=[f'{prefix}_testing'],
                strategy_key='continuous_adversarial_checks',
                consumes=[ArtifactType.CIRCUIT, ArtifactType.TRACE, ArtifactType.WITNESS, ArtifactType.PROOF],
                produces=[ArtifactType.VERIFICATION_RESULT],
                max_execution_ms=1500.0,
                max_artifact_bytes=32768,
                inputs={
                    'artifact_requirements': [
                        {'artifact_type': ArtifactType.CIRCUIT.value, 'produced_by': 'circuit_engineer'},
                        {'artifact_type': ArtifactType.TRACE.value, 'produced_by': 'backend_integration'},
                        {'artifact_type': ArtifactType.WITNESS.value, 'produced_by': 'backend_integration'},
                        {'artifact_type': ArtifactType.PROOF.value, 'produced_by': 'performance_optimization'},
                    ]
                },
            ),
            Task(
                task_id=f'{prefix}_data_integrity',
                domain=TaskDomain.DATA_INTEGRITY,
                description='Recompute the deterministic pipeline and confirm artifact replay matches exactly.',
                priority=TaskPriority.CRITICAL,
                cycle=cycle,
                depends_on=[f'{prefix}_verifier'],
                strategy_key='repeatable_trace_bundle',
                consumes=[ArtifactType.TRACE, ArtifactType.WITNESS, ArtifactType.PROOF],
                produces=[ArtifactType.VERIFICATION_RESULT],
                max_execution_ms=1200.0,
                max_artifact_bytes=32768,
                inputs={
                    'artifact_requirements': [
                        {'artifact_type': ArtifactType.TRACE.value, 'produced_by': 'backend_integration'},
                        {'artifact_type': ArtifactType.WITNESS.value, 'produced_by': 'backend_integration'},
                        {'artifact_type': ArtifactType.PROOF.value, 'produced_by': 'performance_optimization'},
                    ]
                },
            ),
            Task(
                task_id=f'{prefix}_devops',
                domain=TaskDomain.DEVOPS,
                description='Bind the verified pipeline state to the deployment topology.',
                priority=TaskPriority.NORMAL,
                cycle=cycle,
                depends_on=[f'{prefix}_verifier'],
                strategy_key='service_per_folder_topology',
                consumes=[ArtifactType.VERIFICATION_RESULT],
                produces=[ArtifactType.VERIFICATION_RESULT],
                max_execution_ms=750.0,
                max_artifact_bytes=32768,
                inputs={'artifact_requirements': [{'artifact_type': ArtifactType.VERIFICATION_RESULT.value, 'produced_by': 'verifier_agent'}]},
            ),
            Task(
                task_id=f'{prefix}_research',
                domain=TaskDomain.RESEARCH,
                description='Evaluate the verified artifact pipeline for future proving-system upgrades.',
                priority=TaskPriority.NORMAL,
                cycle=cycle,
                depends_on=[f'{prefix}_verifier'],
                strategy_key='plonk_first_migration_path',
                consumes=[ArtifactType.CIRCUIT, ArtifactType.PROOF, ArtifactType.VERIFICATION_RESULT],
                produces=[ArtifactType.VERIFICATION_RESULT],
                max_execution_ms=750.0,
                max_artifact_bytes=32768,
                inputs={
                    'artifact_requirements': [
                        {'artifact_type': ArtifactType.CIRCUIT.value, 'produced_by': 'circuit_engineer'},
                        {'artifact_type': ArtifactType.PROOF.value, 'produced_by': 'performance_optimization'},
                        {'artifact_type': ArtifactType.VERIFICATION_RESULT.value, 'produced_by': 'verifier_agent'},
                    ]
                },
            ),
        ]

    def run_cycle(self, cycle: int = 1) -> CycleExecution:
        artifact_graph = ArtifactGraph()
        self.last_artifact_graph = artifact_graph
        executed_results, blocked_tasks = self._execute_dag(self.build_initial_tasks(cycle), artifact_graph)
        executed_results = sorted(executed_results, key=lambda item: item.task_id)
        for result in executed_results:
            self.memory.apply_entries(result.memory_entries, cycle, result.agent_id)
            metrics = self.performance.record(result)
            self.memory.record_performance(agent_id=result.agent_id, cycle=cycle, tasks_completed=metrics.tasks_completed, tasks_failed=metrics.tasks_failed, avg_duration_ms=metrics.avg_duration_ms, score=metrics.score)
        self.memory.flush()
        replacements = self._replace_underperformers(cycle)
        report = {
            'cycle': cycle,
            'environment': build_environment_manifest(),
            'agent_roster': [
                {
                    'agent_id': agent.agent_id,
                    'domain': agent.domain.value,
                    'version': agent.version,
                    'status': agent.status.value if isinstance(agent.status, AgentStatus) else str(agent.status),
                    'performance_score': agent.performance_score,
                }
                for agent in self.agents
            ],
            'results': [self._result_to_dict(result) for result in executed_results],
            'blocked_tasks': blocked_tasks,
            'replacements': replacements,
            'memory_summary': self.memory.summary(),
            'performance': self.performance.snapshot(),
            'artifact_graph': artifact_graph.to_dict(),
        }
        log_path = self.log_dir / f'zk_engineering_cycle_{cycle:03d}.json'
        log_path.write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
        return CycleExecution(cycle=cycle, results=report['results'], replacements=replacements, memory_summary=report['memory_summary'], performance=report['performance'], artifact_graph=report['artifact_graph'], blocked_tasks=blocked_tasks, log_path=str(log_path))

    def _execute_dag(self, tasks: list[Task], artifact_graph: ArtifactGraph) -> tuple[list[Any], list[dict[str, Any]]]:
        pending = {task.task_id: task for task in tasks}
        completed: dict[str, Any] = {}
        terminal_failures: set[str] = set()
        results = []
        blocked_tasks: list[dict[str, Any]] = []
        while pending:
            ready_assignments: list[tuple[BaseAgent, Task]] = []
            to_remove: list[str] = []
            for task_id, task in sorted(pending.items()):
                failed_dependencies = [dependency for dependency in task.depends_on if dependency in terminal_failures]
                if failed_dependencies:
                    blocked_tasks.append({'task_id': task.task_id, 'domain': task.domain.value, 'reason': 'dependency_failed', 'failed_dependencies': failed_dependencies})
                    to_remove.append(task_id)
                    continue
                if not all(dependency in completed for dependency in task.depends_on):
                    continue
                decision = self.memory.control_decision(domain=task.domain.value, pattern=task.strategy_key)
                if decision['blocked']:
                    blocked_tasks.append({'task_id': task.task_id, 'domain': task.domain.value, 'reason': 'memory_blocked', 'strategy_key': task.strategy_key, 'latest_entry': decision['latest_entry']})
                    terminal_failures.add(task.task_id)
                    to_remove.append(task_id)
                    continue
                prepared_task = self._prepare_task(task, artifact_graph, decision)
                ready_assignments.append((self._assign(prepared_task), prepared_task))
                to_remove.append(task_id)
            for task_id in to_remove:
                pending.pop(task_id, None)
            if not ready_assignments:
                if pending:
                    raise RuntimeError(f'Artifact DAG stalled with unresolved tasks: {sorted(pending.keys())}')
                break
            ready_results = self._execute_ready_set(ready_assignments)
            for result in ready_results:
                if result.status == 'success':
                    completed[result.task_id] = result
                    for artifact in result.produced_artifacts:
                        artifact_graph.add_artifact(artifact, depends_on=result.consumed_artifact_ids)
                else:
                    terminal_failures.add(result.task_id)
                results.append(result)
        return results, blocked_tasks

    def _prepare_task(self, task: Task, artifact_graph: ArtifactGraph, decision: dict[str, Any]) -> Task:
        artifact_inputs, consumed_ids = self._resolve_artifact_inputs(task, artifact_graph)
        merged_inputs = dict(task.inputs)
        merged_inputs['artifact_inputs'] = artifact_inputs
        merged_inputs['preferred_patterns'] = decision['preferred_patterns']
        merged_inputs['failed_patterns'] = decision['failed_patterns']
        merged_inputs['consumed_artifact_ids'] = consumed_ids
        return replace(task, inputs=merged_inputs)

    def _resolve_artifact_inputs(self, task: Task, artifact_graph: ArtifactGraph) -> tuple[dict[str, list[DeterministicArtifact]], list[str]]:
        requirements = list(task.inputs.get('artifact_requirements', []))
        bucket: dict[str, list[DeterministicArtifact]] = {}
        consumed_ids: list[str] = []
        for requirement in requirements:
            artifact = artifact_graph.require(requirement['artifact_type'], produced_by=requirement.get('produced_by'), cycle=task.cycle, artifact_id=requirement.get('artifact_id'))
            bucket.setdefault(artifact.artifact_type.value, []).append(artifact)
            consumed_ids.append(artifact.artifact_id)
        return bucket, sorted(set(consumed_ids))

    def _assign(self, task: Task) -> BaseAgent:
        agent = next((candidate for candidate in self.agents if candidate.accepts(task)), None)
        if agent is None:
            raise RuntimeError(f'No agent available for task {task.task_id} ({task.domain.value})')
        return agent

    def _execute_ready_set(self, assignments: list[tuple[BaseAgent, Task]]):
        results = []
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(assignments))) as executor:
            future_map = {}
            for agent, task in assignments:
                agent.status = AgentStatus.RUNNING
                future_map[executor.submit(agent.run, task, self.memory)] = (agent, task)
            for future in as_completed(future_map):
                agent, task = future_map[future]
                try:
                    result = future.result()
                except Exception as exc:
                    agent.status = AgentStatus.FAILED
                    results.append(agent._make_result(task, status='failure', outputs={}, errors=[str(exc)], memory_entries=[{'type': 'strategy', 'domain': agent.domain.value, 'outcome': 'failure', 'pattern': task.strategy_key or 'agent_execution_exception', 'detail': str(exc), 'tags': ['coordinator', 'exception']}]))
                    continue
                validated = self._enforce_task_constraints(task, result)
                agent.status = AgentStatus.DONE if validated.status == 'success' else AgentStatus.FAILED
                results.append(validated)
        return results

    def _enforce_task_constraints(self, task: Task, result):
        violations = list(result.constraint_violations)
        expected_types = Counter(task.produces)
        actual_types = Counter(artifact.artifact_type for artifact in result.produced_artifacts)
        if expected_types != actual_types:
            violations.append(f"Produced artifact types {sorted(item.value for item in actual_types.elements())} do not match expected {sorted(item.value for item in expected_types.elements())}")
        if task.max_execution_ms is not None and result.duration_ms > task.max_execution_ms:
            violations.append(f'Execution exceeded limit: {round(result.duration_ms, 4)}ms > {task.max_execution_ms}ms')
        if task.max_artifact_bytes is not None:
            for artifact in result.produced_artifacts:
                size = artifact_size_bytes(artifact)
                if size > task.max_artifact_bytes:
                    violations.append(f'Artifact {artifact.artifact_id} exceeded size limit: {size} > {task.max_artifact_bytes}')
        if task.max_circuit_constraints is not None:
            for artifact in result.produced_artifacts:
                if artifact.artifact_type == ArtifactType.CIRCUIT and getattr(artifact, 'constraint_count', 0) > task.max_circuit_constraints:
                    violations.append(f'CIRCUIT {artifact.artifact_id} exceeded complexity limit: {artifact.constraint_count} > {task.max_circuit_constraints}')
        if not result.consumed_artifact_ids:
            result.consumed_artifact_ids = list(task.inputs.get('consumed_artifact_ids', []))
        result.constraint_violations = violations
        if violations:
            result.status = 'failure'
            result.errors = list(result.errors) + violations
            result.produced_artifacts = []
        return result

    def _result_to_dict(self, result) -> dict[str, Any]:
        return {
            'task_id': result.task_id,
            'agent_id': result.agent_id,
            'status': result.status,
            'outputs': result.outputs,
            'errors': result.errors,
            'duration_ms': round(result.duration_ms, 4),
            'consumed_artifact_ids': result.consumed_artifact_ids,
            'constraint_violations': result.constraint_violations,
            'memory_entries': result.memory_entries,
            'produced_artifacts': [
                {'summary': summarize_artifact(artifact), 'payload': artifact.model_dump(mode='python'), 'size_bytes': artifact_size_bytes(artifact)}
                for artifact in result.produced_artifacts
            ],
        }

    def _replace_underperformers(self, cycle: int) -> list[dict[str, Any]]:
        replacements = []
        underperformers = set(self.performance.underperformers())
        if not underperformers:
            return replacements
        fresh_map = {agent.agent_id: agent for agent in build_agent_team()}
        updated_agents = []
        for agent in self.agents:
            if agent.agent_id not in underperformers:
                updated_agents.append(agent)
                continue
            replacement = fresh_map[agent.agent_id]
            old_version = agent.version
            replacement.version = f'{agent.version}-r{cycle}'
            replacement.performance_score = 1.0
            agent.status = AgentStatus.REPLACED
            replacements.append({'agent_id': agent.agent_id, 'old_version': old_version, 'new_version': replacement.version, 'reason': 'underperforming'})
            updated_agents.append(replacement)
        self.agents = updated_agents
        return replacements
