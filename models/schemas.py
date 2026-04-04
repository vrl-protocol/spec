from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from security.guards import enforce_payload_guards
from utils.decimal import money


class ImportCalculationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hs_code: str = Field(pattern=r"^\d{10}$")
    country_of_origin: str = Field(pattern=r"^[A-Z]{2}$")
    customs_value: Decimal = Field(gt=Decimal("0"))
    freight: Decimal = Field(ge=Decimal("0"))
    insurance: Decimal = Field(ge=Decimal("0"))
    quantity: int = Field(ge=1, le=1_000_000)
    shipping_mode: Literal["ocean", "air", "truck"]

    @model_validator(mode="before")
    @classmethod
    def guard_payload(cls, value: object) -> object:
        if isinstance(value, dict):
            enforce_payload_guards(value)
        return value

    @field_validator("hs_code", mode="before")
    @classmethod
    def normalize_hs_code(cls, value: object) -> str:
        text = str(value).strip()
        if not text.isdigit():
            raise ValueError("HS code must contain exactly 10 digits")
        return text

    @field_validator("country_of_origin", mode="before")
    @classmethod
    def normalize_country(cls, value: object) -> str:
        return str(value).strip().upper()

    @field_validator("shipping_mode", mode="before")
    @classmethod
    def normalize_shipping_mode(cls, value: object) -> str:
        return str(value).strip().lower()

    @field_validator("customs_value", "freight", "insurance", mode="before")
    @classmethod
    def normalize_money(cls, value: object) -> Decimal:
        return money(value)


class TraceStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step: str
    rule_ref: str
    inputs: dict[str, str]
    outputs: dict[str, str]


class IntegrityArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_hash: str
    output_hash: str
    trace_hash: str
    integrity_hash: str


class CalculationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_version: str
    dataset_hash: str
    hs_code: str
    country_of_origin: str
    quantity: int
    tariff_rule_ref: str
    tariff_description: str
    unit_customs_value: Decimal
    extended_customs_value: Decimal
    freight: Decimal
    insurance: Decimal
    duty_rate: Decimal
    section_301_rate: Decimal
    duty_amount: Decimal
    section_301_amount: Decimal
    mpf_amount: Decimal
    hmf_amount: Decimal
    landed_cost: Decimal


class CalculationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result: CalculationResult
    trace: list[TraceStep]
    integrity: IntegrityArtifact


class VerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request: ImportCalculationRequest
    response: CalculationResponse


class VerificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["VALID", "INVALID"]
    reason: str
    recomputed_input_hash: str
    recomputed_output_hash: str
    recomputed_trace_hash: str
    recomputed_integrity_hash: str


class RequestRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    input_hash: str
    raw_input: dict[str, Any]
    created_at: datetime


class ResultRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    request_id: UUID
    output_hash: str
    raw_output: dict[str, Any]
    created_at: datetime


class ProofRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    request_id: UUID
    trace_hash: str
    final_proof: str
    integrity_hash: str
    proof_system: str
    circuit_hash: str
    verification_key_hash: str
    proof_bundle: dict[str, Any]
    proof_verified: bool
    created_at: datetime


class AuditEventRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int | None = None
    # chain_id: partition key derived from input_hash % AUDIT_CHAIN_PARTITIONS.
    # Default 0 keeps existing records and in-memory fakes working unchanged.
    chain_id: int = 0
    event_type: str
    reference_id: UUID | None = None
    event_payload: dict[str, Any]
    prev_hash: str
    current_hash: str
    created_at: datetime


class PersistedEvidenceBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request: RequestRecord
    result: ResultRecord
    proof: ProofRecord
    audit_log: AuditEventRecord | None = None


class PersistedCalculationResponse(CalculationResponse):
    evidence: PersistedEvidenceBundle


class PersistedVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request: ImportCalculationRequest


class AuditChainVerificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["VALID", "INVALID"]
    reason: str
    checked_rows: int
    last_hash: str | None = None
    broken_record_id: int | None = None


class PersistedVerificationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verification: VerificationResult
    evidence: PersistedEvidenceBundle | None = None
    audit_chain: AuditChainVerificationResult | None = None
