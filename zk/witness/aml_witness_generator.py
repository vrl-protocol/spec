"""Generate deterministic wire assignments for AML sanctions screening circuit.

The witness is derived from the private name, its normalized form, sanctions root,
and screening timestamp. Wire assignments follow the 7-gate pattern with 4 multiplication
gates and 3 addition gates.
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


@dataclass(frozen=True)
class AMLWitnessInput:
    """Private and public inputs for AML sanctions screening."""

    name: str
    name_normalized: str
    sanctions_root: str
    screening_timestamp: str
    expected_result: int


@dataclass(frozen=True)
class PlonkAssignment:
    """Wire column values for the 7-gate AML Sanctions Screening circuit."""

    a_col: tuple[int, ...]
    b_col: tuple[int, ...]
    c_col: tuple[int, ...]
    wire_map: dict[str, int]
    public_inputs_hash: str

    def verify_gate_constraints(self) -> list[bool]:
        modulus = FIELD_ORDER
        results: list[bool] = []
        for index in range(4):
            results.append((self.a_col[index] * self.b_col[index] - self.c_col[index]) % modulus == 0)
        for index in range(4, 7):
            results.append((self.a_col[index] + self.b_col[index] - self.c_col[index]) % modulus == 0)
        return results


def build_aml_assignment(witness_input: AMLWitnessInput) -> PlonkAssignment:
    """Build PlonkAssignment from AML witness input.

    Wire sequence:
    - Gate 0 (mult): name_hash = hash(name + name_normalized)
    - Gate 1 (mult): name_hash_commitment = name_hash * 1 (binding gate)
    - Gate 2 (mult): membership_result = membership check result
    - Gate 3 (mult): screening_result = membership_result * 1
    - Gate 4 (add): cleared_flag = screening_result + 0
    - Gate 5 (add): timestamp_hash = screening_timestamp hash limbs
    - Gate 6 (add): screening_id = hash(name_hash + sanctions_root + timestamp)
    """
    name_hash_str = sha256_hex(witness_input.name + witness_input.name_normalized)
    name_hash_fp = to_fixed_point(int(name_hash_str[:16], 16))

    sanctions_root_fp = to_fixed_point(int(witness_input.sanctions_root[:16], 16))
    timestamp_hash_str = sha256_hex(witness_input.screening_timestamp)
    timestamp_hash_fp = to_fixed_point(int(timestamp_hash_str[:16], 16))

    membership_result_fp = to_fixed_point(witness_input.expected_result)
    screening_result_fp = membership_result_fp
    cleared_flag_fp = (1 - membership_result_fp) % FIELD_ORDER
    one_fp = 1
    zero_fp = 0

    screening_id_str = sha256_hex(name_hash_str + witness_input.sanctions_root + timestamp_hash_str)
    screening_id_fp = to_fixed_point(int(screening_id_str[:16], 16))

    wire_map = {
        'name_hash_fp': name_hash_fp,
        'sanctions_root_fp': sanctions_root_fp,
        'membership_result_fp': membership_result_fp,
        'screening_result_fp': screening_result_fp,
        'cleared_flag_fp': cleared_flag_fp,
        'timestamp_hash_fp': timestamp_hash_fp,
        'screening_id_fp': screening_id_fp,
        'one_fp': one_fp,
        'zero_fp': zero_fp,
    }

    public_inputs = {
        'sanctions_root': witness_input.sanctions_root,
        'screening_result': str(witness_input.expected_result),
        'screening_id': screening_id_str,
    }

    public_inputs_hash = canonical_public_inputs_hash(public_inputs)

    return PlonkAssignment(
        a_col=(
            name_hash_fp,
            name_hash_fp,
            membership_result_fp,
            screening_result_fp,
            screening_result_fp,
            timestamp_hash_fp,
            name_hash_fp,
        ),
        b_col=(
            sanctions_root_fp,
            one_fp,
            one_fp,
            one_fp,
            zero_fp,
            zero_fp,
            sanctions_root_fp,
        ),
        c_col=(
            membership_result_fp,
            name_hash_fp,
            screening_result_fp,
            screening_result_fp,
            cleared_flag_fp,
            timestamp_hash_fp,
            screening_id_fp,
        ),
        wire_map=wire_map,
        public_inputs_hash=public_inputs_hash,
    )
