"""Generate deterministic wire assignments and public-instance bindings.

The witness is still derived solely from the deterministic engine artifacts.
The verified path consumes the same trace and witness hashes as the fast path.
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


def build_instance_values(landed_cost_fp: int, trace_hash: str, circuit_hash: str, public_inputs_hash: str) -> tuple[int, ...]:
  return (
    landed_cost_fp,
    *hash_hex_to_limbs(trace_hash),
    *hash_hex_to_limbs(circuit_hash),
    *hash_hex_to_limbs(public_inputs_hash),
  )


@dataclass(frozen=True)
class PlonkAssignment:
  """Wire column values for the 8-gate ImportLandedCost circuit."""

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


def _derive_fee_components(private_inputs: dict[str, object]) -> tuple[int, int, int, int]:
  from core.engine import calculate_import_landed_cost
  from models.schemas import ImportCalculationRequest

  request = ImportCalculationRequest.model_validate(private_inputs)
  result = calculate_import_landed_cost(request)
  return (
    to_fixed_point(result.result.duty_amount),
    to_fixed_point(result.result.section_301_amount),
    to_fixed_point(result.result.mpf_amount),
    to_fixed_point(result.result.hmf_amount),
  )


def generate_assignment(witness_artifact: Witness) -> PlonkAssignment:
  public_inputs = witness_artifact.public_inputs
  private_inputs = witness_artifact.private_inputs

  customs_value_fp = to_fixed_point(private_inputs['customs_value'])
  freight_fp = to_fixed_point(private_inputs['freight'])
  insurance_fp = to_fixed_point(private_inputs['insurance'])
  quantity_fp = int(private_inputs['quantity']) % FIELD_ORDER
  landed_cost_fp = to_fixed_point(public_inputs['landed_cost'])

  extended_value_fp = customs_value_fp * quantity_fp % FIELD_ORDER
  duty_amount_fp, s301_amount_fp, mpf_amount_fp, hmf_amount_fp = _derive_fee_components(private_inputs)
  one_fp = 1

  fee_partial_fp = (duty_amount_fp + s301_amount_fp) % FIELD_ORDER
  mpf_hmf_sum_fp = (mpf_amount_fp + hmf_amount_fp) % FIELD_ORDER
  fee_full_fp = (fee_partial_fp + mpf_hmf_sum_fp) % FIELD_ORDER
  base_sum_fp = (extended_value_fp + freight_fp + insurance_fp) % FIELD_ORDER

  wire_map = {
    'customs_value_fp': customs_value_fp,
    'quantity_fp': quantity_fp,
    'extended_value_fp': extended_value_fp,
    'one_fp': one_fp,
    'duty_amount_fp': duty_amount_fp,
    's301_amount_fp': s301_amount_fp,
    'mpf_amount_fp': mpf_amount_fp,
    'hmf_amount_fp': hmf_amount_fp,
    'fee_partial_fp': fee_partial_fp,
    'mpf_hmf_sum_fp': mpf_hmf_sum_fp,
    'fee_full_fp': fee_full_fp,
    'base_sum_fp': base_sum_fp,
    'landed_cost_fp': landed_cost_fp,
    'freight_fp': freight_fp,
    'insurance_fp': insurance_fp,
  }

  public_inputs_hash = canonical_public_inputs_hash(public_inputs)

  return PlonkAssignment(
    a_col=(
      customs_value_fp,
      duty_amount_fp,
      s301_amount_fp,
      mpf_amount_fp,
      hmf_amount_fp,
      duty_amount_fp,
      fee_partial_fp,
      base_sum_fp,
    ),
    b_col=(
      quantity_fp,
      one_fp,
      one_fp,
      one_fp,
      one_fp,
      s301_amount_fp,
      mpf_hmf_sum_fp,
      fee_full_fp,
    ),
    c_col=(
      extended_value_fp,
      duty_amount_fp,
      s301_amount_fp,
      mpf_amount_fp,
      hmf_amount_fp,
      fee_partial_fp,
      fee_full_fp,
      landed_cost_fp,
    ),
    wire_map=wire_map,
    public_inputs_hash=public_inputs_hash,
  )
