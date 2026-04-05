from __future__ import annotations

from coordinator.artifact_graph import ArtifactGraph
from zk.interfaces import ArtifactType, build_circuit_artifact, build_verification_artifact


def test_artifact_graph_tracks_dependencies():
    graph = ArtifactGraph()
    circuit = build_circuit_artifact(
        name='demo_circuit',
        description='demo',
        framework='Plonk',
        public_inputs=['a'],
        private_inputs=['b'],
        constraints=[{'name': 'demo_constraint', 'purpose': 'demo', 'inputs': ['a'], 'outputs': ['b']}],
        produced_by='zk_architect',
        cycle=1,
        complexity_budget=16,
    )
    graph.add_artifact(circuit)
    verification = build_verification_artifact(
        subject_artifact_id=circuit.artifact_id,
        verifier_backend='unit-test',
        status='VALID',
        reason='ok',
        checks=['demo'],
        metadata={},
        produced_by='verifier_agent',
        cycle=1,
    )
    graph.add_artifact(verification, depends_on=[circuit.artifact_id])
    assert graph.node_count() == 2
    assert graph.edge_count() == 1
    assert graph.latest(ArtifactType.CIRCUIT).artifact_id == circuit.artifact_id
    assert graph.dependencies_for(verification.artifact_id) == [circuit.artifact_id]
