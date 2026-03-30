from __future__ import annotations

import json
from pathlib import Path

from agents.zk_unit import build_agent_team
from backend.zk_pipeline import build_stub_pipeline_bundle, compare_repeated_runs
from coordinator.system import ZKCoordinator
from memory.shared_memory import SharedMemory
from zk.interfaces import ArtifactType


def test_agent_team_has_ten_specialists():
    team = build_agent_team()
    assert len(team) == 10
    assert {agent.agent_id for agent in team} == {
        'zk_architect',
        'circuit_engineer',
        'backend_integration',
        'verifier_agent',
        'performance_optimization',
        'security_audit',
        'data_integrity',
        'devops_infrastructure',
        'testing_simulation',
        'research_agent',
    }


def test_stub_pipeline_is_deterministic():
    payload = {
        'hs_code': '8507600000',
        'country_of_origin': 'CN',
        'customs_value': '1200.00',
        'freight': '150.00',
        'insurance': '25.00',
        'quantity': 2,
        'shipping_mode': 'ocean',
    }
    first = build_stub_pipeline_bundle(payload)
    second = build_stub_pipeline_bundle(payload)
    assert first.summary() == second.summary()
    assert first.proof.commitments
    assert first.proof.public_inputs
    assert first.verification_result.status == 'VALID'
    comparison = compare_repeated_runs(payload, iterations=3)
    assert comparison['all_equal'] is True


def test_coordinator_runs_first_cycle_as_artifact_dag(tmp_path: Path):
    coordinator = ZKCoordinator(memory=SharedMemory(tmp_path / 'memory'), log_dir=tmp_path / 'logs')
    execution = coordinator.run_cycle(1)
    assert len(execution.results) == 10
    assert execution.replacements == []
    assert execution.blocked_tasks == []
    assert execution.artifact_graph['node_count'] >= 10
    assert execution.artifact_graph['edge_count'] >= 9
    artifact_types = {node['artifact_type'] for node in execution.artifact_graph['nodes']}
    assert ArtifactType.CIRCUIT.value in artifact_types
    assert ArtifactType.TRACE.value in artifact_types
    assert ArtifactType.WITNESS.value in artifact_types
    assert ArtifactType.PROOF.value in artifact_types
    assert ArtifactType.VERIFICATION_RESULT.value in artifact_types
    report = json.loads(Path(execution.log_path).read_text(encoding='utf-8'))
    assert report['cycle'] == 1
    assert len(report['results']) == 10
    assert report['artifact_graph']['node_count'] == execution.artifact_graph['node_count']
