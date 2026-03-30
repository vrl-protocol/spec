"""Map the ImportLandedCost circuit blueprint to a PLONK-style gate description.

The arithmetic portion remains an 8-gate circuit. Public bindings are tracked
separately so the verified path can expose trace_hash, circuit_hash, and the
canonical public-input hash as instance values without mutating the arithmetic
layout used by the fast path.
"""
from __future__ import annotations

from dataclasses import dataclass

from utils.canonical import canonical_json
from utils.hashing import sha256_hex
from zk.field_utils import FIELD_ORDER

MINUS_ONE = FIELD_ORDER - 1
CIRCUIT_VERSION = 'import-landed-cost-plonk-v2-halo2'
BACKEND_FRAMEWORK = 'halo2'
PUBLIC_BINDING_TARGETS = (
  'landed_cost_fp',
  'trace_hash_limb_0',
  'trace_hash_limb_1',
  'trace_hash_limb_2',
  'trace_hash_limb_3',
  'circuit_hash_limb_0',
  'circuit_hash_limb_1',
  'circuit_hash_limb_2',
  'circuit_hash_limb_3',
  'public_inputs_hash_limb_0',
  'public_inputs_hash_limb_1',
  'public_inputs_hash_limb_2',
  'public_inputs_hash_limb_3',
)


@dataclass(frozen=True)
class PlonkGate:
  gate_id: int
  description: str
  wire_a: str
  wire_b: str
  wire_c: str
  q_L: int
  q_R: int
  q_M: int
  q_O: int
  q_C: int


@dataclass(frozen=True)
class PlonkCircuit:
  version: str
  n_gates: int
  gates: tuple[PlonkGate, ...]
  selector_q_L: tuple[int, ...]
  selector_q_R: tuple[int, ...]
  selector_q_M: tuple[int, ...]
  selector_q_O: tuple[int, ...]
  selector_q_C: tuple[int, ...]
  public_binding_targets: tuple[str, ...]
  circuit_hash: str


_GATES: list[PlonkGate] = [
  PlonkGate(0, 'extended_value', 'customs_value_fp', 'quantity_fp', 'extended_value_fp', 0, 0, 1, MINUS_ONE, 0),
  PlonkGate(1, 'base_duty_copy', 'duty_amount_fp', 'one_fp', 'duty_amount_fp', 0, 0, 1, MINUS_ONE, 0),
  PlonkGate(2, 'section_301_copy', 's301_amount_fp', 'one_fp', 's301_amount_fp', 0, 0, 1, MINUS_ONE, 0),
  PlonkGate(3, 'mpf_amount_copy', 'mpf_amount_fp', 'one_fp', 'mpf_amount_fp', 0, 0, 1, MINUS_ONE, 0),
  PlonkGate(4, 'hmf_amount_copy', 'hmf_amount_fp', 'one_fp', 'hmf_amount_fp', 0, 0, 1, MINUS_ONE, 0),
  PlonkGate(5, 'fee_partial', 'duty_amount_fp', 's301_amount_fp', 'fee_partial_fp', 1, 1, 0, MINUS_ONE, 0),
  PlonkGate(6, 'fee_full', 'fee_partial_fp', 'mpf_hmf_sum_fp', 'fee_full_fp', 1, 1, 0, MINUS_ONE, 0),
  PlonkGate(7, 'landed_cost', 'base_sum_fp', 'fee_full_fp', 'landed_cost_fp', 1, 1, 0, MINUS_ONE, 0),
]


def _compute_circuit_hash(gates: list[PlonkGate]) -> str:
  payload = {
    'version': CIRCUIT_VERSION,
    'framework': BACKEND_FRAMEWORK,
    'gates': [
      {
        'gate_id': gate.gate_id,
        'description': gate.description,
        'q_L': gate.q_L,
        'q_R': gate.q_R,
        'q_M': gate.q_M,
        'q_O': gate.q_O,
        'q_C': gate.q_C,
      }
      for gate in gates
    ],
    'public_binding_targets': list(PUBLIC_BINDING_TARGETS),
  }
  return sha256_hex(canonical_json(payload))


def compile_circuit() -> PlonkCircuit:
  gates = _GATES
  return PlonkCircuit(
    version=CIRCUIT_VERSION,
    n_gates=len(gates),
    gates=tuple(gates),
    selector_q_L=tuple(gate.q_L for gate in gates),
    selector_q_R=tuple(gate.q_R for gate in gates),
    selector_q_M=tuple(gate.q_M for gate in gates),
    selector_q_O=tuple(gate.q_O for gate in gates),
    selector_q_C=tuple(gate.q_C for gate in gates),
    public_binding_targets=PUBLIC_BINDING_TARGETS,
    circuit_hash=_compute_circuit_hash(gates),
  )


def selectors_dict(circuit: PlonkCircuit) -> dict[str, list[int]]:
  return {
    'q_L': list(circuit.selector_q_L),
    'q_R': list(circuit.selector_q_R),
    'q_M': list(circuit.selector_q_M),
    'q_O': list(circuit.selector_q_O),
    'q_C': list(circuit.selector_q_C),
  }
