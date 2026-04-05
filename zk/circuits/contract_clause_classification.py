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
        return {
            'name': self.name,
            'description': self.description,
            'public_inputs': self.public_inputs,
            'private_inputs': self.private_inputs,
            'recommended_framework': self.recommended_framework,
            'constraints': self.constraints,
            'constraint_count': self.constraint_count,
        }


def build_circuit_blueprint() -> CircuitBlueprint:
    constraints = [
        asdict(ConstraintSpec(
            'clause_hash_binding',
            'Hash private clause_text to produce clause_hash, binding the clause to the proof.',
            ['clause_text'],
            ['clause_hash'],
        )),
        asdict(ConstraintSpec(
            'ruleset_commitment',
            'Bind to a specific committed ruleset hash (GDPR_ART9, HIPAA_PHI, SOX_DISCLOSURE, etc.).',
            ['ruleset_id_hash'],
            ['ruleset_id_hash'],
        )),
        asdict(ConstraintSpec(
            'model_output_hash',
            'Hash the AI model\'s raw classification output to prevent post-hoc modification.',
            ['model_raw_output'],
            ['model_output_hash'],
        )),
        asdict(ConstraintSpec(
            'classification_encoding',
            'Encode classification result as field element: HIGH_RISK=3, MEDIUM_RISK=2, LOW_RISK=1, COMPLIANT=0.',
            ['classification_result'],
            ['classification_value'],
        )),
        asdict(ConstraintSpec(
            'risk_threshold_check',
            'Verify that classification_value is within the valid range [0, 3].',
            ['classification_value'],
            ['risk_check_valid'],
        )),
        asdict(ConstraintSpec(
            'ai_id_binding',
            'Bind the AI model\'s AI-ID to the proof to prove which model classified the clause.',
            ['ai_id'],
            ['ai_id'],
        )),
        asdict(ConstraintSpec(
            'audit_chain_hash',
            'Bind to an audit chain entry hash for immutable record-keeping.',
            ['audit_entry_hash'],
            ['audit_entry_hash'],
        )),
    ]
    return CircuitBlueprint(
        name='contract_clause_classification_v1',
        description='ZK circuit for proving AI-based contract clause classification without revealing clause text. Proves classification was computed by applying a committed ruleset hash against a committed clause hash.',
        public_inputs=['ruleset_id_hash', 'ai_id', 'classification_result', 'audit_entry_hash'],
        private_inputs=['clause_text', 'clause_id', 'model_raw_output'],
        recommended_framework='Plonk',
        constraints=constraints,
    )
