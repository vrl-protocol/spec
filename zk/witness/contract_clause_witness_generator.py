"""Generate witness assignments for contract clause classification proofs."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from utils.canonical import canonical_json
from utils.hashing import sha256_hex
from zk.field_utils import FIELD_ORDER
from zk.interfaces import Witness

FIXED_POINT_SCALE = 10**6

# Classification encoding
CLASSIFICATION_ENCODING = {
    'COMPLIANT': 0,
    'LOW_RISK': 1,
    'MEDIUM_RISK': 2,
    'HIGH_RISK': 3,
}


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


def build_instance_values(
    classification_value_fp: int,
    trace_hash: str,
    circuit_hash: str,
    public_inputs_hash: str,
) -> tuple[int, ...]:
    return (
        classification_value_fp,
        *hash_hex_to_limbs(trace_hash),
        *hash_hex_to_limbs(circuit_hash),
        *hash_hex_to_limbs(public_inputs_hash),
    )


@dataclass(frozen=True)
class PlonkAssignment:
    """Wire column values for the 7-gate ContractClauseClassification circuit."""

    a_col: tuple[int, ...]
    b_col: tuple[int, ...]
    c_col: tuple[int, ...]
    wire_map: dict[str, int]
    public_inputs_hash: str

    def verify_gate_constraints(self) -> list[bool]:
        modulus = FIELD_ORDER
        results: list[bool] = []
        # First 4 gates are multiplication gates
        for index in range(4):
            results.append((self.a_col[index] * self.b_col[index] - self.c_col[index]) % modulus == 0)
        # Last 3 gates are addition gates
        for index in range(4, 7):
            results.append((self.a_col[index] + self.b_col[index] - self.c_col[index]) % modulus == 0)
        return results


@dataclass(frozen=True)
class ContractClauseWitnessInput:
    """Input data for contract clause classification witness generation."""

    clause_text: str
    clause_id: str
    model_raw_output: str
    classification_result: str  # One of: COMPLIANT, LOW_RISK, MEDIUM_RISK, HIGH_RISK
    ruleset_id_hash: str
    ai_id: str
    audit_entry_hash: str


def build_contract_clause_assignment(witness_input: ContractClauseWitnessInput) -> PlonkAssignment:
    """
    Build a PlonkAssignment from contract clause witness input.

    Implements 7 gates total:
    - First 4: multiplication gates for hash computations
    - Last 3: addition gates for encoding and validation
    """
    # Validate classification result
    if witness_input.classification_result not in CLASSIFICATION_ENCODING:
        raise ValueError(
            f'Invalid classification_result: {witness_input.classification_result}. '
            f'Must be one of: {list(CLASSIFICATION_ENCODING.keys())}'
        )

    # Compute hashes
    clause_hash = sha256_hex(witness_input.clause_text)
    model_output_hash = sha256_hex(witness_input.model_raw_output)

    # Classification encoding in fixed-point
    classification_code = CLASSIFICATION_ENCODING[witness_input.classification_result]
    classification_value_fp = classification_code * FIXED_POINT_SCALE % FIELD_ORDER

    # Convert hash values to limbs for circuit use
    clause_hash_limbs = hash_hex_to_limbs(clause_hash)
    model_output_hash_limbs = hash_hex_to_limbs(model_output_hash)
    ruleset_hash_limbs = hash_hex_to_limbs(witness_input.ruleset_id_hash)
    audit_hash_limbs = hash_hex_to_limbs(witness_input.audit_entry_hash)

    # Wire assignments: 7 gates total
    # Gate 0 (mult): clause_hash_limbs[0] * model_output_hash_limbs[0] -> product_0
    product_0_fp = (clause_hash_limbs[0] * model_output_hash_limbs[0]) % FIELD_ORDER

    # Gate 1 (mult): ruleset_hash_limbs[0] * classification_value_fp -> product_1
    product_1_fp = (ruleset_hash_limbs[0] * classification_value_fp) % FIELD_ORDER

    # Gate 2 (mult): clause_hash_limbs[1] * model_output_hash_limbs[1] -> product_2
    product_2_fp = (clause_hash_limbs[1] * model_output_hash_limbs[1]) % FIELD_ORDER

    # Gate 3 (mult): audit_hash_limbs[0] * 1 -> product_3 (identity for audit binding)
    product_3_fp = audit_hash_limbs[0] % FIELD_ORDER

    # Gate 4 (add): product_0_fp + product_1_fp -> sum_01
    sum_01_fp = (product_0_fp + product_1_fp) % FIELD_ORDER

    # Gate 5 (add): product_2_fp + product_3_fp -> sum_23
    sum_23_fp = (product_2_fp + product_3_fp) % FIELD_ORDER

    # Gate 6 (add): sum_01_fp + sum_23_fp -> final_proof_element
    final_proof_element_fp = (sum_01_fp + sum_23_fp) % FIELD_ORDER

    one_fp = 1

    # Build wire map for accessibility
    wire_map = {
        'clause_text': int(clause_hash_limbs[0]),
        'clause_hash': int(clause_hash_limbs[0]),
        'model_raw_output': int(model_output_hash_limbs[0]),
        'model_output_hash': int(model_output_hash_limbs[0]),
        'classification_code': classification_code,
        'classification_value_fp': classification_value_fp,
        'ruleset_id_hash': int(ruleset_hash_limbs[0]),
        'ai_id': int(audit_hash_limbs[0]),  # Encoded as limb for field compatibility
        'audit_entry_hash': int(audit_hash_limbs[0]),
        'product_0_fp': product_0_fp,
        'product_1_fp': product_1_fp,
        'product_2_fp': product_2_fp,
        'product_3_fp': product_3_fp,
        'sum_01_fp': sum_01_fp,
        'sum_23_fp': sum_23_fp,
        'final_proof_element_fp': final_proof_element_fp,
        'one_fp': one_fp,
    }

    # Build public inputs
    public_inputs = {
        'ruleset_id_hash': witness_input.ruleset_id_hash,
        'ai_id': witness_input.ai_id,
        'classification_result': witness_input.classification_result,
        'audit_entry_hash': witness_input.audit_entry_hash,
    }

    public_inputs_hash = canonical_public_inputs_hash(public_inputs)

    return PlonkAssignment(
        a_col=(
            clause_hash_limbs[0],
            ruleset_hash_limbs[0],
            clause_hash_limbs[1],
            audit_hash_limbs[0],
            product_0_fp,
            product_2_fp,
            sum_01_fp,
        ),
        b_col=(
            model_output_hash_limbs[0],
            classification_value_fp,
            model_output_hash_limbs[1],
            one_fp,
            product_1_fp,
            product_3_fp,
            sum_23_fp,
        ),
        c_col=(
            product_0_fp,
            product_1_fp,
            product_2_fp,
            product_3_fp,
            sum_01_fp,
            sum_23_fp,
            final_proof_element_fp,
        ),
        wire_map=wire_map,
        public_inputs_hash=public_inputs_hash,
    )
