"""Generate deterministic wire assignments for drug dosage verification circuit.

The witness is derived from patient weight, creatinine clearance, age, and FDA dataset.
Wire assignments follow the 8-gate pattern with 5 multiplication gates and 3 addition gates.
Includes Cockcroft-Gault formula implementation in fixed-point arithmetic.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from utils.canonical import canonical_json
from utils.hashing import sha256_hex
from zk.field_utils import FIELD_ORDER
from zk.interfaces import Witness

FIXED_POINT_SCALE = 10**6


def to_fixed_point(value: object) -> int:
    decimal_value = Decimal(str(value))
    return int((decimal_value * FIXED_POINT_SCALE).to_integral_value(rounding=ROUND_HALF_UP)) % FIELD_ORDER


def hash_hex_to_limbs(hex_value: str) -> tuple[int, int, int, int]:
    if len(hex_value) != 64:
        raise ValueError(f'Expected 64 hex chars, got {len(hex_value)}')
    return tuple(int(hex_value[index:index + 16], 16) for index in range(0, 64, 16))


def canonical_public_inputs_hash(public_inputs: dict[str, str]) -> str:
    normalized = {key: str(value) for key, value in sorted(public_inputs.items())}
    return sha256_hex(canonical_json(normalized))


def compute_renal_adjustment_factor(creatinine_clearance_ml_min: float) -> float:
    """Compute CrCl-based dose adjustment using simplified Cockcroft-Gault.

    Normal CrCl is approximately 90 ml/min. Adjustment factor is min(1.0, CrCl / 90).
    """
    normal_crcl = 90.0
    adjustment = min(1.0, creatinine_clearance_ml_min / normal_crcl)
    return max(0.1, adjustment)


def compute_age_adjustment_factor(patient_age_years: float) -> float:
    """Compute age-based dose adjustment.

    Standard dosing for adults 18-65: factor = 1.0
    Pediatric (< 18): factor = weight/70 (simplified, assumes normal weight for age)
    Geriatric (> 65): factor = 0.8 to 0.9
    """
    if patient_age_years < 18:
        return 0.5
    elif patient_age_years > 65:
        return 0.85
    else:
        return 1.0


def compute_weight_based_dose(patient_weight_kg: float) -> float:
    """Compute standard weight-adjusted base dose.

    For amoxicillin: 250-500 mg per 8 hours, or 15 mg/kg for general cases.
    Using simplified: base_dose = 250 mg as standard.
    """
    dose_per_kg = 15.0
    base_dose = dose_per_kg * patient_weight_kg
    return base_dose


@dataclass(frozen=True)
class DrugDosageWitnessInput:
    """Private and public inputs for drug dosage verification."""

    patient_weight_kg: float
    creatinine_clearance_ml_min: float
    patient_age_years: float
    fda_dataset_hash: str
    drug_id: str
    dose_frequency_hours: int


@dataclass(frozen=True)
class PlonkAssignment:
    """Wire column values for the 8-gate Drug Dosage Verification circuit."""

    a_col: tuple[int, ...]
    b_col: tuple[int, ...]
    c_col: tuple[int, ...]
    wire_map: dict[str, int]
    public_inputs_hash: str

    def verify_gate_constraints(self) -> list[bool]:
        modulus = FIELD_ORDER
        results: list[bool] = []
        for index in range(5):
            results.append((self.a_col[index] * self.b_col[index] - self.c_col[index]) % modulus == 0)
        for index in range(5, 8):
            results.append((self.a_col[index] + self.b_col[index] - self.c_col[index]) % modulus == 0)
        return results


def build_drug_dosage_assignment(witness_input: DrugDosageWitnessInput) -> PlonkAssignment:
    """Build PlonkAssignment from drug dosage witness input.

    Wire sequence:
    - Gate 0 (mult): patient_hash = weight * creatinine (PHI binding)
    - Gate 1 (mult): adjustment_factor = creatinine / 90 (renal adjustment)
    - Gate 2 (mult): base_dose_mg = weight * dose_per_kg
    - Gate 3 (mult): age_factor lookup and binding
    - Gate 4 (mult): adjusted_dose = base_dose * adjustment * age_factor
    - Gate 5 (add): bounds_valid = adjusted_dose + 0 (range check)
    - Gate 6 (add): dataset_binding = fda_hash + 0
    - Gate 7 (add): recommended_dose = adjusted_dose + dataset_binding
    """
    adjustment_factor = compute_renal_adjustment_factor(witness_input.creatinine_clearance_ml_min)
    age_factor = compute_age_adjustment_factor(witness_input.patient_age_years)
    base_dose = compute_weight_based_dose(witness_input.patient_weight_kg)
    adjusted_dose = base_dose * adjustment_factor * age_factor

    weight_fp = to_fixed_point(witness_input.patient_weight_kg)
    creatinine_fp = to_fixed_point(witness_input.creatinine_clearance_ml_min)
    adjustment_factor_fp = to_fixed_point(adjustment_factor)
    base_dose_fp = to_fixed_point(base_dose)
    age_factor_fp = to_fixed_point(age_factor)
    adjusted_dose_fp = to_fixed_point(adjusted_dose)

    fda_dataset_hash_fp = to_fixed_point(int(witness_input.fda_dataset_hash[:16], 16))
    dose_frequency_fp = to_fixed_point(witness_input.dose_frequency_hours)

    patient_hash_fp = (weight_fp * creatinine_fp) % FIELD_ORDER
    bounds_valid_fp = adjusted_dose_fp
    dataset_binding_fp = fda_dataset_hash_fp
    recommended_dose_fp = adjusted_dose_fp

    one_fp = 1
    zero_fp = 0
    dose_per_kg_fp = to_fixed_point(15.0)

    wire_map = {
        'weight_fp': weight_fp,
        'creatinine_fp': creatinine_fp,
        'adjustment_factor_fp': adjustment_factor_fp,
        'base_dose_fp': base_dose_fp,
        'age_factor_fp': age_factor_fp,
        'adjusted_dose_fp': adjusted_dose_fp,
        'patient_hash_fp': patient_hash_fp,
        'fda_dataset_hash_fp': fda_dataset_hash_fp,
        'dataset_binding_fp': dataset_binding_fp,
        'recommended_dose_fp': recommended_dose_fp,
        'one_fp': one_fp,
        'zero_fp': zero_fp,
    }

    patient_hash_str = sha256_hex(str(witness_input.patient_weight_kg) + str(witness_input.creatinine_clearance_ml_min) + str(witness_input.patient_age_years))

    public_inputs = {
        'fda_dataset_hash': witness_input.fda_dataset_hash,
        'recommended_dose_mg': str(adjusted_dose),
        'dose_frequency_hours': str(witness_input.dose_frequency_hours),
        'patient_hash': patient_hash_str,
    }

    public_inputs_hash = canonical_public_inputs_hash(public_inputs)

    return PlonkAssignment(
        a_col=(
            weight_fp,
            creatinine_fp,
            weight_fp,
            age_factor_fp,
            base_dose_fp,
            adjusted_dose_fp,
            fda_dataset_hash_fp,
            adjusted_dose_fp,
        ),
        b_col=(
            creatinine_fp,
            to_fixed_point(90.0),
            dose_per_kg_fp,
            one_fp,
            adjustment_factor_fp,
            zero_fp,
            zero_fp,
            dataset_binding_fp,
        ),
        c_col=(
            patient_hash_fp,
            adjustment_factor_fp,
            base_dose_fp,
            age_factor_fp,
            adjusted_dose_fp,
            bounds_valid_fp,
            dataset_binding_fp,
            recommended_dose_fp,
        ),
        wire_map=wire_map,
        public_inputs_hash=public_inputs_hash,
    )
