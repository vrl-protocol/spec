"""Test vectors for drug dosage verification witness generation."""
from __future__ import annotations

from typing import Any


def get_test_vectors() -> list[dict[str, Any]]:
    """Return 3 test vectors: normal renal function, impaired renal function, pediatric."""
    return [
        {
            'name': 'normal_renal_function_adult',
            'input': {
                'patient_weight_kg': 70.0,
                'creatinine_clearance_ml_min': 90.0,
                'patient_age_years': 45,
                'fda_dataset_hash': '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
                'drug_id': 'amoxicillin_250mg',
                'dose_frequency_hours': 8,
            },
            'expected_output': {
                'adjustment_factor': 1.0,
                'age_factor': 1.0,
                'base_dose_mg': 1050.0,
                'adjusted_dose_mg': 1050.0,
            },
        },
        {
            'name': 'impaired_renal_function_dose_reduction',
            'input': {
                'patient_weight_kg': 70.0,
                'creatinine_clearance_ml_min': 30.0,
                'patient_age_years': 70,
                'fda_dataset_hash': '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
                'drug_id': 'amoxicillin_250mg',
                'dose_frequency_hours': 12,
            },
            'expected_output': {
                'adjustment_factor': 0.3333,
                'age_factor': 0.85,
                'base_dose_mg': 1050.0,
                'adjusted_dose_mg': 298.5,
            },
        },
        {
            'name': 'pediatric_weight_adjustment',
            'input': {
                'patient_weight_kg': 25.0,
                'creatinine_clearance_ml_min': 85.0,
                'patient_age_years': 12,
                'fda_dataset_hash': '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
                'drug_id': 'amoxicillin_125mg',
                'dose_frequency_hours': 8,
            },
            'expected_output': {
                'adjustment_factor': 0.9444,
                'age_factor': 0.5,
                'base_dose_mg': 375.0,
                'adjusted_dose_mg': 177.0,
            },
        },
    ]
