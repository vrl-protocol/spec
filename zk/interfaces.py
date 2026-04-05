from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from models.schemas import TraceStep
from utils.canonical import canonical_json
from utils.hashing import sha256_hex


class ArtifactType(str, Enum):
  CIRCUIT = 'circuit'
  TRACE = 'trace'
  WITNESS = 'witness'
  PROOF = 'proof'
  VERIFICATION_RESULT = 'verification_result'


class DeterministicArtifact(BaseModel):
  model_config = ConfigDict(extra='forbid', frozen=True)

  artifact_type: ArtifactType
  artifact_id: str
  produced_by: str
  cycle: int

  def canonical_payload(self) -> str:
    return canonical_json(self.model_dump(mode='python'))

  def content_hash(self) -> str:
    return sha256_hex(self.canonical_payload())


class CircuitConstraint(BaseModel):
  model_config = ConfigDict(extra='forbid', frozen=True)

  name: str
  purpose: str
  inputs: list[str]
  outputs: list[str]


class Circuit(DeterministicArtifact):
  artifact_type: Literal[ArtifactType.CIRCUIT] = ArtifactType.CIRCUIT
  name: str
  description: str
  framework: str
  public_inputs: list[str]
  private_inputs: list[str]
  constraints: list[CircuitConstraint]
  constraint_count: int
  complexity_budget: int

  @model_validator(mode='after')
  def validate_constraint_count(self) -> 'Circuit':
    if self.constraint_count != len(self.constraints):
      raise ValueError('constraint_count must match the number of constraints')
    return self


class Trace(DeterministicArtifact):
  artifact_type: Literal[ArtifactType.TRACE] = ArtifactType.TRACE
  input_hash: str
  steps: list[TraceStep]
  canonical_trace: str
  trace_hash: str

  @model_validator(mode='after')
  def validate_trace_hash(self) -> 'Trace':
    expected_canonical = canonical_json([step.model_dump(mode='python') for step in self.steps])
    if self.canonical_trace != expected_canonical:
      raise ValueError('canonical_trace does not match the canonicalized trace steps')
    if self.trace_hash != sha256_hex(expected_canonical):
      raise ValueError('trace_hash does not match canonical_trace')
    return self


class Witness(DeterministicArtifact):
  artifact_type: Literal[ArtifactType.WITNESS] = ArtifactType.WITNESS
  trace_artifact_id: str
  input_hash: str
  output_hash: str
  trace_hash: str
  public_inputs: dict[str, str]
  private_inputs: dict[str, Any]
  canonical_witness: str
  witness_hash: str

  @model_validator(mode='after')
  def validate_witness_hash(self) -> 'Witness':
    witness_payload = {
      'trace_artifact_id': self.trace_artifact_id,
      'input_hash': self.input_hash,
      'output_hash': self.output_hash,
      'trace_hash': self.trace_hash,
      'public_inputs': self.public_inputs,
      'private_inputs': self.private_inputs,
    }
    expected_canonical = canonical_json(witness_payload)
    if self.canonical_witness != expected_canonical:
      raise ValueError('canonical_witness does not match the witness payload')
    if self.witness_hash != sha256_hex(expected_canonical):
      raise ValueError('witness_hash does not match canonical_witness')
    return self


class Proof(DeterministicArtifact):
  artifact_type: Literal[ArtifactType.PROOF] = ArtifactType.PROOF
  proof_system: str
  circuit_artifact_id: str
  witness_artifact_id: str
  commitments: list[str]
  public_inputs: list[str]
  metadata: dict[str, str]
  proof_blob_hex: str
  proof_hash: str
  input_hash: str
  output_hash: str
  trace_hash: str
  final_proof: str

  @computed_field(return_type=str)
  @property
  def proof_bytes(self) -> str:
    return self.proof_blob_hex

  @computed_field(return_type=str)
  @property
  def proving_system(self) -> str:
    return self.proof_system

  @computed_field(return_type=str)
  @property
  def circuit_hash(self) -> str:
    return self.metadata.get('circuit_hash', '')

  @model_validator(mode='after')
  def validate_proof_hash(self) -> 'Proof':
    payload = {
      'proof_system': self.proof_system,
      'circuit_artifact_id': self.circuit_artifact_id,
      'witness_artifact_id': self.witness_artifact_id,
      'commitments': self.commitments,
      'public_inputs': self.public_inputs,
      'metadata': self.metadata,
      'proof_blob_hex': self.proof_blob_hex,
      'input_hash': self.input_hash,
      'output_hash': self.output_hash,
      'trace_hash': self.trace_hash,
      'final_proof': self.final_proof,
    }
    expected_hash = sha256_hex(canonical_json(payload))
    if self.proof_hash != expected_hash:
      raise ValueError('proof_hash does not match the canonical proof payload')
    return self


class VerificationResult(DeterministicArtifact):
  artifact_type: Literal[ArtifactType.VERIFICATION_RESULT] = ArtifactType.VERIFICATION_RESULT
  subject_artifact_id: str
  verifier_backend: str
  status: Literal['VALID', 'INVALID']
  reason: str
  checks: list[str] = Field(default_factory=list)
  metadata: dict[str, str] = Field(default_factory=dict)
  verification_hash: str

  @model_validator(mode='after')
  def validate_verification_hash(self) -> 'VerificationResult':
    payload = {
      'subject_artifact_id': self.subject_artifact_id,
      'verifier_backend': self.verifier_backend,
      'status': self.status,
      'reason': self.reason,
      'checks': self.checks,
      'metadata': self.metadata,
    }
    expected_hash = sha256_hex(canonical_json(payload))
    if self.verification_hash != expected_hash:
      raise ValueError('verification_hash does not match the canonical verification payload')
    return self


ArtifactModel = Annotated[
  Circuit | Trace | Witness | Proof | VerificationResult,
  Field(discriminator='artifact_type'),
]


def artifact_id_for(artifact_type: ArtifactType | str, payload: object) -> str:
  kind = artifact_type.value if isinstance(artifact_type, ArtifactType) else str(artifact_type)
  return f'{kind}_{sha256_hex(canonical_json(payload))[:24]}'


def build_circuit_artifact(*, name: str, description: str, framework: str, public_inputs: list[str], private_inputs: list[str], constraints: list[dict[str, Any]], produced_by: str, cycle: int, complexity_budget: int) -> Circuit:
  payload = {
    'name': name,
    'description': description,
    'framework': framework,
    'public_inputs': public_inputs,
    'private_inputs': private_inputs,
    'constraints': constraints,
    'constraint_count': len(constraints),
    'complexity_budget': complexity_budget,
    'produced_by': produced_by,
    'cycle': cycle,
  }
  return Circuit(
    artifact_id=artifact_id_for(ArtifactType.CIRCUIT, payload),
    produced_by=produced_by,
    cycle=cycle,
    name=name,
    description=description,
    framework=framework,
    public_inputs=public_inputs,
    private_inputs=private_inputs,
    constraints=[CircuitConstraint.model_validate(item) for item in constraints],
    constraint_count=len(constraints),
    complexity_budget=complexity_budget,
  )


def build_trace_artifact(*, input_hash: str, steps: list[TraceStep], produced_by: str, cycle: int) -> Trace:
  canonical_trace = canonical_json([step.model_dump(mode='python') for step in steps])
  trace_hash = sha256_hex(canonical_trace)
  payload = {
    'input_hash': input_hash,
    'canonical_trace': canonical_trace,
    'trace_hash': trace_hash,
    'produced_by': produced_by,
    'cycle': cycle,
  }
  return Trace(
    artifact_id=artifact_id_for(ArtifactType.TRACE, payload),
    produced_by=produced_by,
    cycle=cycle,
    input_hash=input_hash,
    steps=steps,
    canonical_trace=canonical_trace,
    trace_hash=trace_hash,
  )


def build_witness_artifact(*, trace_artifact_id: str, input_hash: str, output_hash: str, trace_hash: str, public_inputs: dict[str, str], private_inputs: dict[str, Any], produced_by: str, cycle: int) -> Witness:
  witness_payload = {
    'trace_artifact_id': trace_artifact_id,
    'input_hash': input_hash,
    'output_hash': output_hash,
    'trace_hash': trace_hash,
    'public_inputs': public_inputs,
    'private_inputs': private_inputs,
  }
  canonical_witness = sha256_hex(canonical_json(witness_payload)) if False else canonical_json(witness_payload)
  witness_hash = sha256_hex(canonical_witness)
  artifact_payload = dict(witness_payload)
  artifact_payload.update({'witness_hash': witness_hash, 'produced_by': produced_by, 'cycle': cycle})
  return Witness(
    artifact_id=artifact_id_for(ArtifactType.WITNESS, artifact_payload),
    produced_by=produced_by,
    cycle=cycle,
    trace_artifact_id=trace_artifact_id,
    input_hash=input_hash,
    output_hash=output_hash,
    trace_hash=trace_hash,
    public_inputs=public_inputs,
    private_inputs=private_inputs,
    canonical_witness=canonical_witness,
    witness_hash=witness_hash,
  )


def build_proof_artifact(*, proof_system: str, circuit_artifact_id: str, witness_artifact_id: str, commitments: list[str], public_inputs: list[str], metadata: dict[str, str], proof_blob_hex: str, input_hash: str, output_hash: str, trace_hash: str, final_proof: str, produced_by: str, cycle: int) -> Proof:
  payload = {
    'proof_system': proof_system,
    'circuit_artifact_id': circuit_artifact_id,
    'witness_artifact_id': witness_artifact_id,
    'commitments': commitments,
    'public_inputs': public_inputs,
    'metadata': metadata,
    'proof_blob_hex': proof_blob_hex,
    'input_hash': input_hash,
    'output_hash': output_hash,
    'trace_hash': trace_hash,
    'final_proof': final_proof,
  }
  proof_hash = sha256_hex(canonical_json(payload))
  artifact_payload = dict(payload)
  artifact_payload.update({'proof_hash': proof_hash, 'produced_by': produced_by, 'cycle': cycle})
  return Proof(
    artifact_id=artifact_id_for(ArtifactType.PROOF, artifact_payload),
    produced_by=produced_by,
    cycle=cycle,
    proof_system=proof_system,
    circuit_artifact_id=circuit_artifact_id,
    witness_artifact_id=witness_artifact_id,
    commitments=commitments,
    public_inputs=public_inputs,
    metadata=metadata,
    proof_blob_hex=proof_blob_hex,
    proof_hash=proof_hash,
    input_hash=input_hash,
    output_hash=output_hash,
    trace_hash=trace_hash,
    final_proof=final_proof,
  )


def build_verification_artifact(*, subject_artifact_id: str, verifier_backend: str, status: Literal['VALID', 'INVALID'], reason: str, checks: list[str], metadata: dict[str, str], produced_by: str, cycle: int) -> VerificationResult:
  payload = {
    'subject_artifact_id': subject_artifact_id,
    'verifier_backend': verifier_backend,
    'status': status,
    'reason': reason,
    'checks': checks,
    'metadata': metadata,
  }
  verification_hash = sha256_hex(canonical_json(payload))
  artifact_payload = dict(payload)
  artifact_payload.update({'verification_hash': verification_hash, 'produced_by': produced_by, 'cycle': cycle})
  return VerificationResult(
    artifact_id=artifact_id_for(ArtifactType.VERIFICATION_RESULT, artifact_payload),
    produced_by=produced_by,
    cycle=cycle,
    subject_artifact_id=subject_artifact_id,
    verifier_backend=verifier_backend,
    status=status,
    reason=reason,
    checks=checks,
    metadata=metadata,
    verification_hash=verification_hash,
  )


def artifact_size_bytes(artifact: DeterministicArtifact) -> int:
  return len(artifact.canonical_payload().encode('utf-8'))


def summarize_artifact(artifact: DeterministicArtifact) -> dict[str, object]:
  return {
    'artifact_id': artifact.artifact_id,
    'artifact_type': artifact.artifact_type.value,
    'produced_by': artifact.produced_by,
    'cycle': artifact.cycle,
    'content_hash': artifact.content_hash(),
  }

