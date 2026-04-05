from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ConstraintSpec:
    name: str
    purpose: str
    inputs: list[str]
    outputs: list[str]


@dataclass(frozen=True)
class CircuitBlueprint:
    name: str
    description: str
    public_inputs: list[str]
    private_inputs: list[str]
    recommended_framework: str
    constraints: list[dict[str, Any]]

    @property
    def constraint_count(self) -> int:
        return len(self.constraints)

    def to_dict(self) -> dict[str, Any]:
        return {'name': self.name, 'description': self.description, 'public_inputs': self.public_inputs, 'private_inputs': self.private_inputs, 'recommended_framework': self.recommended_framework, 'constraints': self.constraints, 'constraint_count': self.constraint_count}


def build_circuit_blueprint() -> CircuitBlueprint:
    constraints = [
        asdict(ConstraintSpec('canonical_name_hash', 'Hash the private name to produce a deterministic name_hash binding.', ['name', 'name_normalized'], ['name_hash'])),
        asdict(ConstraintSpec('name_hash_commitment', 'Bind name_hash to a public commitment preventing substitution.', ['name_hash'], ['name_hash_commitment'])),
        asdict(ConstraintSpec('sanctions_set_membership', 'Check name_hash against the sanctions list Merkle root.', ['name_hash', 'sanctions_root'], ['membership_result'])),
        asdict(ConstraintSpec('result_binding', 'Bind the screening result to the proof.', ['membership_result'], ['screening_result'])),
        asdict(ConstraintSpec('cleared_flag', 'Assert screening_result is 0 if cleared, or record flag if hit.', ['screening_result'], ['cleared_flag'])),
        asdict(ConstraintSpec('audit_timestamp_hash', 'Bind current timestamp hash to the proof for replay protection.', ['screening_timestamp'], ['timestamp_hash'])),
        asdict(ConstraintSpec('screening_id_hash', 'Produce unique screening_id from name_hash, sanctions_root, and timestamp.', ['name_hash', 'sanctions_root', 'timestamp_hash'], ['screening_id'])),
    ]
    return CircuitBlueprint(
        name='aml_sanctions_screening_v1',
        description='Privacy-preserving AML/sanctions screening circuit that proves a name was screened and cleared without revealing the name.',
        public_inputs=['sanctions_root', 'screening_result', 'screening_id'],
        private_inputs=['name', 'name_normalized', 'screening_timestamp'],
        recommended_framework='Plonk',
        constraints=constraints,
    )
