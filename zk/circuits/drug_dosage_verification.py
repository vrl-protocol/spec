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
        asdict(ConstraintSpec('patient_hash', 'Hash private patient identifiers to produce patient_hash for PHI binding.', ['patient_weight_kg', 'creatinine_clearance_ml_min', 'patient_age_years'], ['patient_hash'])),
        asdict(ConstraintSpec('renal_adjustment_factor', 'Compute creatinine clearance-based dose adjustment factor.', ['creatinine_clearance_ml_min'], ['adjustment_factor'])),
        asdict(ConstraintSpec('weight_based_dose', 'Compute weight-adjusted base dose using standard dosing table.', ['patient_weight_kg'], ['base_dose_mg'])),
        asdict(ConstraintSpec('age_adjustment', 'Apply age-based dose modifier.', ['patient_age_years'], ['age_factor'])),
        asdict(ConstraintSpec('adjusted_dose', 'Apply renal and age adjustments to base dose.', ['base_dose_mg', 'adjustment_factor', 'age_factor'], ['adjusted_dose_mg'])),
        asdict(ConstraintSpec('dosing_bounds_check', 'Verify result is within FDA-approved dose bounds.', ['adjusted_dose_mg'], ['bounds_valid'])),
        asdict(ConstraintSpec('fda_dataset_commitment', 'Bind to signed FDA dataset hash for integrity.', ['fda_dataset_hash'], ['dataset_binding'])),
        asdict(ConstraintSpec('final_dose_hash', 'Produce final recommended_dose_mg and hash for integrity.', ['adjusted_dose_mg', 'dataset_binding'], ['recommended_dose_mg'])),
    ]
    return CircuitBlueprint(
        name='drug_dosage_verification_v1',
        description='Healthcare circuit that proves a drug dosage recommendation was computed correctly using FDA-approved formulas without revealing patient identity.',
        public_inputs=['fda_dataset_hash', 'recommended_dose_mg', 'dose_frequency_hours', 'patient_hash'],
        private_inputs=['patient_weight_kg', 'creatinine_clearance_ml_min', 'patient_age_years', 'drug_id'],
        recommended_framework='Plonk',
        constraints=constraints,
    )
