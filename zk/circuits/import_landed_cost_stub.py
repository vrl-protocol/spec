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
        asdict(ConstraintSpec('canonical_input_hash', 'Bind private request inputs to a deterministic input hash.', ['hs_code', 'country_of_origin', 'shipping_mode', 'customs_value', 'freight', 'insurance', 'quantity'], ['input_hash'])),
        asdict(ConstraintSpec('tariff_lookup_commitment', 'Commit to the tariff row and rates used by the calculation.', ['hs_code', 'country_of_origin'], ['duty_rate', 'section_301_rate'])),
        asdict(ConstraintSpec('extended_value', 'Compute customs_value * quantity.', ['customs_value', 'quantity'], ['extended_customs_value'])),
        asdict(ConstraintSpec('base_duty', 'Apply the duty rate to extended customs value.', ['extended_customs_value', 'duty_rate'], ['duty_amount'])),
        asdict(ConstraintSpec('section_301', 'Apply section 301 surcharge conditionally by origin.', ['extended_customs_value', 'country_of_origin', 'section_301_rate'], ['section_301_amount'])),
        asdict(ConstraintSpec('mpf_clamp', 'Apply the minimum/maximum clamped MPF rule.', ['extended_customs_value'], ['mpf_amount'])),
        asdict(ConstraintSpec('hmf_rule', 'Apply HMF only when shipping mode is ocean.', ['extended_customs_value', 'shipping_mode'], ['hmf_amount'])),
        asdict(ConstraintSpec('landed_cost_sum', 'Aggregate all cost components into the final landed cost.', ['extended_customs_value', 'freight', 'insurance', 'duty_amount', 'section_301_amount', 'mpf_amount', 'hmf_amount'], ['landed_cost'])),
    ]
    return CircuitBlueprint(name='import_landed_cost_stub_v1', description='Circuit-oriented decomposition of the deterministic U.S. import landed-cost engine.', public_inputs=['hs_code', 'country_of_origin', 'shipping_mode', 'landed_cost'], private_inputs=['customs_value', 'freight', 'insurance', 'quantity'], recommended_framework='Plonk', constraints=constraints)
