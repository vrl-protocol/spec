from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from models.schemas import CalculationResult, TraceStep


class VerifiedTrainingRecord(BaseModel):
    model_config = ConfigDict(extra='forbid')

    dataset_version: str
    record_id: str
    request_id: UUID
    proof_id: UUID
    created_at: datetime
    verification_status: str
    input_hash: str
    output_hash: str
    trace_hash: str
    witness_hash: str
    integrity_hash: str
    final_proof: str
    circuit_hash: str
    verification_key_hash: str
    proof_system: str
    input_payload: dict[str, Any]
    result_payload: CalculationResult
    trace: list[TraceStep]
    proof_bundle: dict[str, Any]


class VerifiedDatasetExport(BaseModel):
    model_config = ConfigDict(extra='forbid')

    dataset_version: str
    exported_at: datetime
    total_candidates: int
    exportable_records: int
    skipped_records: int
    records: list[VerifiedTrainingRecord]


class VerifiedDatasetMoatMetrics(BaseModel):
    model_config = ConfigDict(extra='forbid')

    dataset_version: str
    measured_at: datetime
    total_candidates: int
    exportable_records: int
    skipped_records: int
    unique_input_hashes: int
    unique_output_hashes: int
    unique_trace_hashes: int
    unique_circuit_hashes: int
    unique_verification_keys: int
    unique_hs_codes: int
    unique_origin_countries: int
    proof_systems: list[str] = Field(default_factory=list)
    exportability_ratio: float
