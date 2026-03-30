from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from zk.interfaces import ArtifactType, DeterministicArtifact


@dataclass(frozen=True)
class ArtifactEdge:
    parent_artifact_id: str
    child_artifact_id: str
    relationship: str = 'depends_on'

    def as_dict(self) -> dict[str, str]:
        return {
            'parent_artifact_id': self.parent_artifact_id,
            'child_artifact_id': self.child_artifact_id,
            'relationship': self.relationship,
        }


class ArtifactGraph:
    def __init__(self) -> None:
        self._artifacts: dict[str, DeterministicArtifact] = {}
        self._edges: list[ArtifactEdge] = []
        self._by_type: dict[ArtifactType, list[str]] = {artifact_type: [] for artifact_type in ArtifactType}
        self._by_producer: dict[str, list[str]] = {}

    def add_artifact(self, artifact: DeterministicArtifact, *, depends_on: Iterable[str] | None = None) -> DeterministicArtifact:
        existing = self._artifacts.get(artifact.artifact_id)
        if existing is not None:
            if existing.content_hash() != artifact.content_hash():
                raise ValueError(f'Artifact collision detected for {artifact.artifact_id}')
            return existing
        self._artifacts[artifact.artifact_id] = artifact
        self._by_type[artifact.artifact_type].append(artifact.artifact_id)
        self._by_producer.setdefault(artifact.produced_by, []).append(artifact.artifact_id)
        for parent_artifact_id in sorted(set(depends_on or [])):
            if parent_artifact_id not in self._artifacts:
                raise KeyError(f'Unknown parent artifact {parent_artifact_id}')
            self._edges.append(ArtifactEdge(parent_artifact_id=parent_artifact_id, child_artifact_id=artifact.artifact_id))
        self._edges.sort(key=lambda edge: (edge.parent_artifact_id, edge.child_artifact_id, edge.relationship))
        return artifact

    def get(self, artifact_id: str) -> DeterministicArtifact:
        try:
            return self._artifacts[artifact_id]
        except KeyError as exc:
            raise KeyError(f'Artifact not found: {artifact_id}') from exc

    def artifacts_by_type(self, artifact_type: ArtifactType | str) -> list[DeterministicArtifact]:
        normalized = artifact_type if isinstance(artifact_type, ArtifactType) else ArtifactType(str(artifact_type))
        return [self._artifacts[artifact_id] for artifact_id in self._by_type[normalized]]

    def artifacts_by_producer(self, produced_by: str, *, artifact_type: ArtifactType | str | None = None, cycle: int | None = None) -> list[DeterministicArtifact]:
        artifact_ids = self._by_producer.get(produced_by, [])
        artifacts = [self._artifacts[artifact_id] for artifact_id in artifact_ids]
        if artifact_type is not None:
            normalized = artifact_type if isinstance(artifact_type, ArtifactType) else ArtifactType(str(artifact_type))
            artifacts = [artifact for artifact in artifacts if artifact.artifact_type == normalized]
        if cycle is not None:
            artifacts = [artifact for artifact in artifacts if artifact.cycle == cycle]
        return sorted(artifacts, key=lambda artifact: (artifact.cycle, artifact.artifact_id))

    def latest(self, artifact_type: ArtifactType | str, *, produced_by: str | None = None, cycle: int | None = None) -> DeterministicArtifact:
        candidates = self.artifacts_by_type(artifact_type)
        if produced_by is not None:
            candidates = [artifact for artifact in candidates if artifact.produced_by == produced_by]
        if cycle is not None:
            candidates = [artifact for artifact in candidates if artifact.cycle == cycle]
        if not candidates:
            kind = artifact_type.value if isinstance(artifact_type, ArtifactType) else str(artifact_type)
            raise KeyError(f'No artifact available for type={kind!r}, produced_by={produced_by!r}, cycle={cycle!r}')
        return sorted(candidates, key=lambda artifact: (artifact.cycle, artifact.artifact_id))[-1]

    def require(self, artifact_type: ArtifactType | str, *, produced_by: str | None = None, cycle: int | None = None, artifact_id: str | None = None) -> DeterministicArtifact:
        if artifact_id is not None:
            artifact = self.get(artifact_id)
            normalized = artifact_type if isinstance(artifact_type, ArtifactType) else ArtifactType(str(artifact_type))
            if artifact.artifact_type != normalized:
                raise TypeError(f'Artifact {artifact_id} has type {artifact.artifact_type.value}, expected {normalized.value}')
            return artifact
        return self.latest(artifact_type, produced_by=produced_by, cycle=cycle)

    def dependencies_for(self, artifact_id: str) -> list[str]:
        return sorted(edge.parent_artifact_id for edge in self._edges if edge.child_artifact_id == artifact_id)

    def dependents_for(self, artifact_id: str) -> list[str]:
        return sorted(edge.child_artifact_id for edge in self._edges if edge.parent_artifact_id == artifact_id)

    def node_count(self) -> int:
        return len(self._artifacts)

    def edge_count(self) -> int:
        return len(self._edges)

    def to_dict(self) -> dict[str, object]:
        artifacts = [
            {
                'artifact_id': artifact.artifact_id,
                'artifact_type': artifact.artifact_type.value,
                'produced_by': artifact.produced_by,
                'cycle': artifact.cycle,
                'content_hash': artifact.content_hash(),
                'payload': artifact.model_dump(mode='python'),
            }
            for artifact in sorted(self._artifacts.values(), key=lambda item: item.artifact_id)
        ]
        edges = [edge.as_dict() for edge in self._edges]
        return {
            'nodes': artifacts,
            'edges': edges,
            'node_count': len(artifacts),
            'edge_count': len(edges),
        }
