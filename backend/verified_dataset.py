from __future__ import annotations

from collections.abc import Iterable

from models.schemas import CalculationResponse, PersistedCalculationResponse, PersistedEvidenceBundle
from utils.canonical import canonical_json
from utils.hashing import sha256_hex
from utils.time import utc_now
from models.verified_dataset import (
    VerifiedDatasetExport,
    VerifiedDatasetMoatMetrics,
    VerifiedTrainingRecord,
)
from zk.interfaces import Proof
from backend.trace_adapter import build_trace_packet
from backend.proof_export import verify_proof_bundle
from utils.hashing import constant_time_equal


VERIFIED_DATASET_VERSION = 'verified-training-record-v1'


def build_verified_training_record(
    persisted: PersistedCalculationResponse,
    *,
    zk_proof: Proof,
    witness_hash: str,
    verification_key_hash: str,
    proof_bundle: dict[str, object],
) -> VerifiedTrainingRecord:
    if proof_bundle.get('proof') is None:
        raise ValueError('proof_bundle must include a proof payload')

    record_payload = {
        'dataset_version': VERIFIED_DATASET_VERSION,
        'request_id': str(persisted.evidence.request.id),
        'proof_id': str(persisted.evidence.proof.id),
        'input_hash': persisted.integrity.input_hash,
        'output_hash': persisted.integrity.output_hash,
        'trace_hash': persisted.integrity.trace_hash,
        'witness_hash': witness_hash,
        'integrity_hash': persisted.integrity.integrity_hash,
        'final_proof': zk_proof.final_proof,
        'circuit_hash': zk_proof.circuit_hash,
        'verification_key_hash': verification_key_hash,
        'proof_system': zk_proof.proof_system,
    }
    record_id = sha256_hex(canonical_json(record_payload))
    return VerifiedTrainingRecord(
        dataset_version=VERIFIED_DATASET_VERSION,
        record_id=record_id,
        request_id=persisted.evidence.request.id,
        proof_id=persisted.evidence.proof.id,
        created_at=persisted.evidence.proof.created_at,
        verification_status='VERIFIED',
        input_hash=persisted.integrity.input_hash,
        output_hash=persisted.integrity.output_hash,
        trace_hash=persisted.integrity.trace_hash,
        witness_hash=witness_hash,
        integrity_hash=persisted.integrity.integrity_hash,
        final_proof=zk_proof.final_proof,
        circuit_hash=zk_proof.circuit_hash,
        verification_key_hash=verification_key_hash,
        proof_system=zk_proof.proof_system,
        input_payload=persisted.evidence.request.raw_input,
        result_payload=persisted.result,
        trace=persisted.trace,
        proof_bundle=proof_bundle,
    )


def build_verified_training_record_from_evidence(
    evidence: PersistedEvidenceBundle,
) -> VerifiedTrainingRecord:
    if not evidence.proof.proof_verified:
        raise ValueError('Only proof-verified evidence may be exported into the training dataset')
    if evidence.proof.proof_system != 'plonk':
        raise ValueError('legacy record')

    proof_bundle = evidence.proof.proof_bundle
    bundle_verification = verify_proof_bundle(proof_bundle)
    if not bundle_verification['valid']:
        raise ValueError(f"Persisted proof bundle is not externally valid: {bundle_verification['reason']}")

    response = CalculationResponse.model_validate(evidence.result.raw_output)
    persisted = PersistedCalculationResponse(
        result=response.result,
        trace=response.trace,
        integrity=response.integrity,
        evidence=evidence,
    )
    trace_packet = build_trace_packet(evidence.request.raw_input, produced_by='verified_dataset_export', cycle=1)
    zk_proof = Proof.model_validate(proof_bundle['proof'])
    if not constant_time_equal(trace_packet.response.integrity.input_hash, evidence.request.input_hash):
        raise ValueError('Persisted request hash does not match recomputed deterministic input hash')
    if not constant_time_equal(trace_packet.response.integrity.output_hash, evidence.result.output_hash):
        raise ValueError('Persisted result hash does not match recomputed deterministic output hash')
    if not constant_time_equal(trace_packet.response.integrity.trace_hash, evidence.proof.trace_hash):
        raise ValueError('Persisted trace hash does not match recomputed deterministic trace hash')
    if not constant_time_equal(zk_proof.final_proof, evidence.proof.final_proof):
        raise ValueError('Persisted final proof does not match bundled proof payload')
    if not constant_time_equal(zk_proof.circuit_hash, evidence.proof.circuit_hash):
        raise ValueError('Persisted circuit hash does not match bundled proof payload')
    return build_verified_training_record(
        persisted,
        zk_proof=zk_proof,
        witness_hash=trace_packet.witness_artifact.witness_hash,
        verification_key_hash=evidence.proof.verification_key_hash,
        proof_bundle=proof_bundle,
    )


def export_verified_dataset(
    bundles: Iterable[PersistedEvidenceBundle],
) -> VerifiedDatasetExport:
    records: list[VerifiedTrainingRecord] = []
    total_candidates = 0
    skipped_records = 0

    for bundle in bundles:
        total_candidates += 1
        try:
            records.append(build_verified_training_record_from_evidence(bundle))
        except ValueError:
            skipped_records += 1

    return VerifiedDatasetExport(
        dataset_version=VERIFIED_DATASET_VERSION,
        exported_at=utc_now(),
        total_candidates=total_candidates,
        exportable_records=len(records),
        skipped_records=skipped_records,
        records=records,
    )


def compute_moat_metrics(dataset: VerifiedDatasetExport) -> VerifiedDatasetMoatMetrics:
    records = dataset.records
    exportability_ratio = 0.0
    if dataset.total_candidates > 0:
        exportability_ratio = len(records) / dataset.total_candidates

    return VerifiedDatasetMoatMetrics(
        dataset_version=dataset.dataset_version,
        measured_at=utc_now(),
        total_candidates=dataset.total_candidates,
        exportable_records=dataset.exportable_records,
        skipped_records=dataset.skipped_records,
        unique_input_hashes=len({record.input_hash for record in records}),
        unique_output_hashes=len({record.output_hash for record in records}),
        unique_trace_hashes=len({record.trace_hash for record in records}),
        unique_circuit_hashes=len({record.circuit_hash for record in records}),
        unique_verification_keys=len({record.verification_key_hash for record in records}),
        unique_hs_codes=len({record.result_payload.hs_code for record in records}),
        unique_origin_countries=len({record.result_payload.country_of_origin for record in records}),
        proof_systems=sorted({record.proof_system for record in records}),
        exportability_ratio=exportability_ratio,
    )
