from __future__ import annotations

import time
from typing import Any

from agents.base import BaseAgent, Task, TaskDomain
from backend.trace_adapter import build_trace_packet
from backend.zk_pipeline import compare_repeated_runs, simulate_input_variants
from core.sample import REFERENCE_REQUEST
from infra.environment import build_environment_manifest
from zk.architecture import get_architecture_blueprint
from zk.circuits.import_landed_cost_stub import build_circuit_blueprint
from zk.interfaces import (
    ArtifactType,
    Trace,
    build_circuit_artifact,
    build_proof_artifact,
    build_verification_artifact,
    build_witness_artifact,
    summarize_artifact,
)
from zk.provers.stub_prover import benchmark_stub_prover, build_default_circuit_artifact, prove_artifacts
from zk.verifiers.stub_verifier import verify_artifacts


def _artifact_inputs(task: Task) -> dict[str, list[Any]]:
    bucket = task.inputs.get('artifact_inputs', {})
    return bucket if isinstance(bucket, dict) else {}


def _artifacts(task: Task, artifact_type: ArtifactType) -> list[Any]:
    return list(_artifact_inputs(task).get(artifact_type.value, []))


def _require_artifact(task: Task, artifact_type: ArtifactType):
    artifacts = _artifacts(task, artifact_type)
    if not artifacts:
        raise RuntimeError(f'Missing required artifact {artifact_type.value} for task {task.task_id}')
    return artifacts[-1]


def _consumed_ids(task: Task) -> list[str]:
    artifact_ids: list[str] = []
    for values in _artifact_inputs(task).values():
        for artifact in values:
            artifact_ids.append(artifact.artifact_id)
    return sorted(set(artifact_ids))


class ZKArchitectAgent(BaseAgent):
    agent_id = 'zk_architect'
    domain = TaskDomain.ARCHITECTURE

    def run(self, task: Task, memory: Any):
        start = time.perf_counter()
        blueprint = get_architecture_blueprint()
        circuit = build_default_circuit_artifact(produced_by=self.agent_id, cycle=task.cycle)
        outputs = {
            'selected_target_framework': blueprint['target_framework'],
            'stub_framework': blueprint['stub_framework'],
            'phases': blueprint['delivery_phases'],
            'preferred_patterns': task.inputs.get('preferred_patterns', []),
            'artifact': summarize_artifact(circuit),
        }
        memory_entries = [
            {
                'type': 'strategy',
                'domain': self.domain.value,
                'outcome': 'success',
                'pattern': 'layered_proof_architecture',
                'detail': 'Selected a layered architecture that keeps deterministic VRL computation separate from future prover backends.',
                'tags': ['architecture', 'zk', 'success'],
            }
        ]
        return self._make_result(task, outputs=outputs, memory_entries=memory_entries, produced_artifacts=[circuit], consumed_artifact_ids=_consumed_ids(task), start_time=start)


class CircuitEngineerAgent(BaseAgent):
    agent_id = 'circuit_engineer'
    domain = TaskDomain.CIRCUIT

    def run(self, task: Task, memory: Any):
        start = time.perf_counter()
        seed_circuit = _require_artifact(task, ArtifactType.CIRCUIT)
        blueprint = build_circuit_blueprint()
        refined_circuit = build_circuit_artifact(
            name=f'{blueprint.name}_refined',
            description=f'{blueprint.description} Refined for artifact-driven DAG execution.',
            framework=seed_circuit.framework,
            public_inputs=list(seed_circuit.public_inputs),
            private_inputs=list(seed_circuit.private_inputs),
            constraints=[constraint.model_dump(mode='python') for constraint in seed_circuit.constraints],
            produced_by=self.agent_id,
            cycle=task.cycle,
            complexity_budget=seed_circuit.complexity_budget,
        )
        outputs = {
            'circuit_name': refined_circuit.name,
            'constraint_count': refined_circuit.constraint_count,
            'public_inputs': refined_circuit.public_inputs,
            'private_inputs': refined_circuit.private_inputs,
            'artifact': summarize_artifact(refined_circuit),
        }
        memory_entries = [
            {
                'type': 'strategy',
                'domain': self.domain.value,
                'outcome': 'success',
                'pattern': 'trace_to_constraints_mapping',
                'detail': 'Mapped each deterministic landed-cost trace step into a typed artifact-compatible circuit constraint family.',
                'tags': ['circuits', 'constraints'],
            },
            {
                'type': 'circuit',
                'circuit_name': refined_circuit.name,
                'constraint_count': refined_circuit.constraint_count,
                'proving_system': refined_circuit.framework,
                'proving_time_ms': 0.0,
                'description': refined_circuit.description,
                'code_snippet': '\n'.join(constraint.name for constraint in refined_circuit.constraints),
            },
        ]
        return self._make_result(task, outputs=outputs, memory_entries=memory_entries, produced_artifacts=[refined_circuit], consumed_artifact_ids=_consumed_ids(task), start_time=start)


class BackendIntegrationAgent(BaseAgent):
    agent_id = 'backend_integration'
    domain = TaskDomain.BACKEND

    def run(self, task: Task, memory: Any):
        start = time.perf_counter()
        circuit = _require_artifact(task, ArtifactType.CIRCUIT)
        packet = build_trace_packet(REFERENCE_REQUEST, produced_by=self.agent_id, cycle=task.cycle)
        outputs = {
            'circuit_artifact_id': circuit.artifact_id,
            'trace': summarize_artifact(packet.trace_artifact),
            'witness': summarize_artifact(packet.witness_artifact),
            'trace_length': len(packet.response.trace),
            'artifact_paths': {'trace_adapter': 'backend/trace_adapter.py'},
        }
        memory_entries = [
            {
                'type': 'strategy',
                'domain': self.domain.value,
                'outcome': 'success',
                'pattern': 'deterministic_trace_extraction',
                'detail': 'Connected the deterministic VRL trace to typed trace and witness artifacts without introducing network calls or hidden state.',
                'tags': ['backend', 'integration'],
            }
        ]
        return self._make_result(task, outputs=outputs, memory_entries=memory_entries, produced_artifacts=[packet.trace_artifact, packet.witness_artifact], consumed_artifact_ids=_consumed_ids(task), start_time=start)


class VerifierAgent(BaseAgent):
    agent_id = 'verifier_agent'
    domain = TaskDomain.VERIFICATION

    def run(self, task: Task, memory: Any):
        start = time.perf_counter()
        circuit = _require_artifact(task, ArtifactType.CIRCUIT)
        trace = _require_artifact(task, ArtifactType.TRACE)
        witness = _require_artifact(task, ArtifactType.WITNESS)
        proof = _require_artifact(task, ArtifactType.PROOF)
        verification = verify_artifacts(circuit, trace, witness, proof, produced_by=self.agent_id, cycle=task.cycle)
        outputs = {
            'verified': verification.status == 'VALID',
            'reason': verification.reason,
            'checks': list(verification.checks),
            'artifact': summarize_artifact(verification),
        }
        memory_entries = [
            {
                'type': 'strategy',
                'domain': self.domain.value,
                'outcome': 'success' if verification.status == 'VALID' else 'failure',
                'pattern': 'structured_stub_verifier',
                'detail': 'Validated a structured verifier path that can later be replaced by a real on-chain or off-chain verifier backend.',
                'tags': ['verification', 'compatibility'],
            }
        ]
        return self._make_result(task, outputs=outputs, memory_entries=memory_entries, produced_artifacts=[verification], consumed_artifact_ids=_consumed_ids(task), start_time=start)


class PerformanceOptimizationAgent(BaseAgent):
    agent_id = 'performance_optimization'
    domain = TaskDomain.PERFORMANCE

    def run(self, task: Task, memory: Any):
        start = time.perf_counter()
        circuit = _require_artifact(task, ArtifactType.CIRCUIT)
        trace = _require_artifact(task, ArtifactType.TRACE)
        witness = _require_artifact(task, ArtifactType.WITNESS)
        proof = prove_artifacts(circuit, trace, witness, produced_by=self.agent_id, cycle=task.cycle)
        benchmark = benchmark_stub_prover(iterations=3)
        outputs = {
            'proof': summarize_artifact(proof),
            'benchmark': benchmark,
            'preferred_patterns': task.inputs.get('preferred_patterns', []),
        }
        memory_entries = [
            {
                'type': 'strategy',
                'domain': self.domain.value,
                'outcome': 'success',
                'pattern': 'structured_stub_proof',
                'detail': 'Produced a structured deterministic proof envelope with commitments, public inputs, and prover metadata.',
                'tags': ['performance', 'prover', 'structured-proof'],
            }
        ]
        return self._make_result(task, outputs=outputs, memory_entries=memory_entries, produced_artifacts=[proof], consumed_artifact_ids=_consumed_ids(task), start_time=start)


class SecurityAuditAgent(BaseAgent):
    agent_id = 'security_audit'
    domain = TaskDomain.SECURITY

    def run(self, task: Task, memory: Any):
        start = time.perf_counter()
        circuit = _require_artifact(task, ArtifactType.CIRCUIT)
        trace = _require_artifact(task, ArtifactType.TRACE)
        witness = _require_artifact(task, ArtifactType.WITNESS)
        proof = _require_artifact(task, ArtifactType.PROOF)
        malformed_trace_rejected = False
        try:
            Trace(
                artifact_id=trace.artifact_id,
                produced_by=self.agent_id,
                cycle=task.cycle,
                input_hash=trace.input_hash,
                steps=trace.steps,
                canonical_trace='[]',
                trace_hash=trace.trace_hash,
            )
        except ValueError:
            malformed_trace_rejected = True
        corrupted_witness = build_witness_artifact(
            trace_artifact_id=trace.artifact_id,
            input_hash=witness.input_hash,
            output_hash='0' * 64,
            trace_hash=witness.trace_hash,
            public_inputs=dict(witness.public_inputs),
            private_inputs=dict(witness.private_inputs),
            produced_by=self.agent_id,
            cycle=task.cycle,
        )
        corrupted_verification = verify_artifacts(circuit, trace, corrupted_witness, proof, produced_by=self.agent_id, cycle=task.cycle)
        replay_proof = build_proof_artifact(
            proof_system=proof.proof_system,
            circuit_artifact_id=circuit.artifact_id,
            witness_artifact_id=corrupted_witness.artifact_id,
            commitments=list(proof.commitments),
            public_inputs=list(proof.public_inputs),
            metadata=dict(proof.metadata),
            proof_blob_hex=proof.proof_blob_hex,
            input_hash=corrupted_witness.input_hash,
            output_hash=corrupted_witness.output_hash,
            trace_hash=corrupted_witness.trace_hash,
            final_proof=proof.final_proof,
            produced_by=self.agent_id,
            cycle=task.cycle,
        )
        replay_verification = verify_artifacts(circuit, trace, corrupted_witness, replay_proof, produced_by=self.agent_id, cycle=task.cycle)
        checks = [
            'malformed_trace_rejected' if malformed_trace_rejected else 'malformed_trace_accepted',
            'corrupted_witness_invalid' if corrupted_verification.status == 'INVALID' else 'corrupted_witness_accepted',
            'replayed_proof_invalid' if replay_verification.status == 'INVALID' else 'replayed_proof_accepted',
        ]
        status = 'VALID' if malformed_trace_rejected and corrupted_verification.status == 'INVALID' and replay_verification.status == 'INVALID' else 'INVALID'
        verification = build_verification_artifact(
            subject_artifact_id=proof.artifact_id,
            verifier_backend='continuous-adversarial-audit',
            status=status,
            reason='adversarial mutations rejected' if status == 'VALID' else 'adversarial mutation bypass detected',
            checks=checks,
            metadata={'replay_subject': replay_proof.artifact_id},
            produced_by=self.agent_id,
            cycle=task.cycle,
        )
        memory_entries = [
            {
                'type': 'strategy',
                'domain': self.domain.value,
                'outcome': 'success' if status == 'VALID' else 'failure',
                'pattern': 'continuous_adversarial_checks',
                'detail': 'Injected malformed traces, corrupted witnesses, and replayed proofs to ensure invalid artifact states are rejected.',
                'tags': ['security', 'adversarial'],
            }
        ]
        if status != 'VALID':
            memory_entries.append(
                {
                    'type': 'vulnerability',
                    'name': 'artifact-pipeline-adversarial-bypass',
                    'description': 'One or more adversarial artifact mutations passed validation in the Stage 4 pipeline.',
                    'severity': 'high',
                    'mitigation': 'Halt the pipeline and tighten typed artifact validation before continuing.',
                    'affected_domains': [self.domain.value, TaskDomain.VERIFICATION.value, TaskDomain.DATA_INTEGRITY.value],
                }
            )
        outputs = {'status': status, 'checks': checks, 'artifact': summarize_artifact(verification)}
        return self._make_result(task, status='success' if status == 'VALID' else 'failure', outputs=outputs, memory_entries=memory_entries, produced_artifacts=[verification], consumed_artifact_ids=_consumed_ids(task), start_time=start)


class DataIntegrityAgent(BaseAgent):
    agent_id = 'data_integrity'
    domain = TaskDomain.DATA_INTEGRITY

    def run(self, task: Task, memory: Any):
        start = time.perf_counter()
        trace = _require_artifact(task, ArtifactType.TRACE)
        witness = _require_artifact(task, ArtifactType.WITNESS)
        proof = _require_artifact(task, ArtifactType.PROOF)
        comparison = compare_repeated_runs(REFERENCE_REQUEST, iterations=3)
        replay_packet = build_trace_packet(REFERENCE_REQUEST, produced_by='backend_integration', cycle=task.cycle)
        replay_consistent = (
            replay_packet.trace_artifact.trace_hash == trace.trace_hash
            and replay_packet.witness_artifact.witness_hash == witness.witness_hash
            and proof.final_proof == replay_packet.response.proof.integrity_hash
            and comparison['all_equal']
        )
        verification = build_verification_artifact(
            subject_artifact_id=proof.artifact_id,
            verifier_backend='data-integrity-replay-check',
            status='VALID' if replay_consistent else 'INVALID',
            reason='deterministic replay matches stored artifacts' if replay_consistent else 'deterministic replay diverged from stored artifacts',
            checks=[
                'repeated_bundle_equal' if comparison['all_equal'] else 'repeated_bundle_diverged',
                'trace_hash_replayed' if replay_packet.trace_artifact.trace_hash == trace.trace_hash else 'trace_hash_mismatch',
                'witness_hash_replayed' if replay_packet.witness_artifact.witness_hash == witness.witness_hash else 'witness_hash_mismatch',
                'final_proof_replayed' if proof.final_proof == replay_packet.response.proof.integrity_hash else 'final_proof_mismatch',
            ],
            metadata={'reference_input_hash': proof.input_hash},
            produced_by=self.agent_id,
            cycle=task.cycle,
        )
        memory_entries = [
            {
                'type': 'strategy',
                'domain': self.domain.value,
                'outcome': 'success' if verification.status == 'VALID' else 'failure',
                'pattern': 'repeatable_trace_bundle',
                'detail': 'Confirmed that repeated executions produce the same trace, witness, and final proof artifacts.',
                'tags': ['integrity', 'determinism'],
            }
        ]
        outputs = {'comparison': comparison, 'artifact': summarize_artifact(verification)}
        return self._make_result(task, status='success' if verification.status == 'VALID' else 'failure', outputs=outputs, memory_entries=memory_entries, produced_artifacts=[verification], consumed_artifact_ids=_consumed_ids(task), start_time=start)


class DevOpsInfrastructureAgent(BaseAgent):
    agent_id = 'devops_infrastructure'
    domain = TaskDomain.DEVOPS

    def run(self, task: Task, memory: Any):
        start = time.perf_counter()
        verification = _require_artifact(task, ArtifactType.VERIFICATION_RESULT)
        manifest = build_environment_manifest()
        readiness = build_verification_artifact(
            subject_artifact_id=verification.artifact_id,
            verifier_backend='devops-readiness-audit',
            status='VALID' if verification.status == 'VALID' else 'INVALID',
            reason='deployment topology remains aligned with the verified proof pipeline' if verification.status == 'VALID' else 'verification gate failed before deployment topology sign-off',
            checks=['environment_manifest_loaded', 'verifier_gate_checked'],
            metadata={'component_count': str(len(manifest.get('components', {})))},
            produced_by=self.agent_id,
            cycle=task.cycle,
        )
        outputs = {'environment': manifest, 'artifact': summarize_artifact(readiness)}
        memory_entries = [
            {
                'type': 'strategy',
                'domain': self.domain.value,
                'outcome': 'success' if readiness.status == 'VALID' else 'failure',
                'pattern': 'service_per_folder_topology',
                'detail': 'Documented the shared repository topology and verified it against the current proof pipeline state.',
                'tags': ['devops', 'topology'],
            }
        ]
        return self._make_result(task, status='success' if readiness.status == 'VALID' else 'failure', outputs=outputs, memory_entries=memory_entries, produced_artifacts=[readiness], consumed_artifact_ids=_consumed_ids(task), start_time=start)


class TestingSimulationAgent(BaseAgent):
    agent_id = 'testing_simulation'
    domain = TaskDomain.TESTING

    def run(self, task: Task, memory: Any):
        start = time.perf_counter()
        proof = _require_artifact(task, ArtifactType.PROOF)
        verification = _require_artifact(task, ArtifactType.VERIFICATION_RESULT)
        variants = simulate_input_variants()
        status = 'VALID' if verification.status == 'VALID' and variants['same_input_consistent'] and variants['hashes_differ_for_variant'] else 'INVALID'
        testing_result = build_verification_artifact(
            subject_artifact_id=proof.artifact_id,
            verifier_backend='testing-simulation',
            status=status,
            reason='artifact pipeline smoke tests passed' if status == 'VALID' else 'artifact pipeline smoke tests failed',
            checks=[
                'verifier_status_valid' if verification.status == 'VALID' else 'verifier_status_invalid',
                'same_input_consistent' if variants['same_input_consistent'] else 'same_input_inconsistent',
                'variant_hashes_differ' if variants['hashes_differ_for_variant'] else 'variant_hashes_same',
            ],
            metadata={'baseline_input_hash': variants['baseline_input_hash'], 'variant_input_hash': variants['variant_input_hash']},
            produced_by=self.agent_id,
            cycle=task.cycle,
        )
        outputs = {'variants': variants, 'artifact': summarize_artifact(testing_result)}
        memory_entries = [
            {
                'type': 'strategy',
                'domain': self.domain.value,
                'outcome': 'success' if status == 'VALID' else 'failure',
                'pattern': 'artifact_pipeline_smoke',
                'detail': 'Executed deterministic same-input and varied-input pipeline simulations against the typed artifact flow.',
                'tags': ['testing', 'simulation'],
            }
        ]
        return self._make_result(task, status='success' if status == 'VALID' else 'failure', outputs=outputs, memory_entries=memory_entries, produced_artifacts=[testing_result], consumed_artifact_ids=_consumed_ids(task), start_time=start)


class ResearchAgent(BaseAgent):
    agent_id = 'research_agent'
    domain = TaskDomain.RESEARCH

    def run(self, task: Task, memory: Any):
        start = time.perf_counter()
        circuit = _require_artifact(task, ArtifactType.CIRCUIT)
        proof = _require_artifact(task, ArtifactType.PROOF)
        verification = _require_artifact(task, ArtifactType.VERIFICATION_RESULT)
        blueprint = get_architecture_blueprint()
        roadmap = build_verification_artifact(
            subject_artifact_id=proof.artifact_id,
            verifier_backend='research-roadmap-evaluator',
            status='VALID' if verification.status == 'VALID' and proof.proof_system == 'sha256-structured-stub' else 'INVALID',
            reason='migration path remains compatible with a future plonkish backend' if verification.status == 'VALID' else 'verification gate failed before roadmap sign-off',
            checks=['verification_gate_checked', 'structured_stub_confirmed', 'circuit_framework_reviewed'],
            metadata={'recommended_framework': circuit.framework, 'target_framework': blueprint['target_framework']},
            produced_by=self.agent_id,
            cycle=task.cycle,
        )
        outputs = {
            'near_term': blueprint['recommended_next_steps'],
            'frameworks_reviewed': blueprint['framework_candidates'],
            'migration_path': blueprint['migration_path'],
            'artifact': summarize_artifact(roadmap),
        }
        memory_entries = [
            {
                'type': 'strategy',
                'domain': self.domain.value,
                'outcome': 'success' if roadmap.status == 'VALID' else 'failure',
                'pattern': 'plonk_first_migration_path',
                'detail': 'Recommended a plonkish proving path first, while preserving compatibility with future verifier upgrades.',
                'tags': ['research', 'roadmap'],
            }
        ]
        return self._make_result(task, status='success' if roadmap.status == 'VALID' else 'failure', outputs=outputs, memory_entries=memory_entries, produced_artifacts=[roadmap], consumed_artifact_ids=_consumed_ids(task), start_time=start)


def build_agent_team() -> list[BaseAgent]:
    return [
        ZKArchitectAgent(),
        CircuitEngineerAgent(),
        BackendIntegrationAgent(),
        VerifierAgent(),
        PerformanceOptimizationAgent(),
        SecurityAuditAgent(),
        DataIntegrityAgent(),
        DevOpsInfrastructureAgent(),
        TestingSimulationAgent(),
        ResearchAgent(),
    ]
