from __future__ import annotations

import json
from pathlib import Path

from vrl import (
    AIIdentityBuilder,
    ComputationBuilder,
    ProofBuilder,
    ProofBundleBuilder,
    Verifier,
    compute_bundle_id_from_integrity,
    compute_input_hash,
    compute_integrity_hash,
    compute_output_hash,
    compute_proof_hash,
    compute_trace_hash,
    sha256,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "examples" / "sdk_demo_bundle.json"


def main() -> int:
    inputs = {
        "hs_code": "8507600000",
        "country_of_origin": "CN",
        "customs_value": "1200.00",
        "freight": "150.00",
        "insurance": "25.00",
        "quantity": "2",
        "shipping_mode": "ocean",
    }
    outputs = {
        "landed_cost": "2150.12",
        "duty_amount": "735.12",
        "mpf_amount": "32.71",
        "hmf_amount": "3.00",
    }
    trace = [
        {
            "step": 1,
            "rule_ref": "trade/import-landed-cost@2.0.0",
            "inputs": {"customs_value": "1200.00", "quantity": "2"},
            "outputs": {"extended_value": "2400.00"},
        },
        {
            "step": 2,
            "rule_ref": "trade/import-landed-cost@2.0.0",
            "inputs": {"extended_value": "2400.00", "tariff_rate": "0.3063"},
            "outputs": {"duty_amount": "735.12"},
        },
    ]

    input_hash = compute_input_hash(inputs)
    output_hash = compute_output_hash(outputs)
    trace_hash = compute_trace_hash(trace)
    integrity_hash = compute_integrity_hash(input_hash, output_hash, trace_hash)

    circuit_id = "trade/import-landed-cost@2.0.0"
    circuit_version = "2.0.0"
    circuit_hash = sha256(
        json.dumps(
            {
                "circuit_id": circuit_id,
                "circuit_version": circuit_version,
                "spec_version": "vrl/circuit/1.0",
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )

    ai_identity = (
        AIIdentityBuilder()
        .compute_ai_id(
            model_weights_hash=sha256("demo-model-weights"),
            runtime_hash=sha256("python-3.11|deterministic-runtime"),
            config_hash=sha256(json.dumps({"temperature": 0, "top_p": 1}, sort_keys=True)),
            provider_id="io.vrl.demo",
            model_name="vrl-deterministic-engine",
            model_version="1.0.0",
        )
        .set_execution_environment("deterministic")
        .build()
    )

    public_inputs = [input_hash, output_hash]
    proof_system = "sha256-deterministic"
    proof_bytes = sha256("demo-proof-bytes:" + integrity_hash)
    verification_key_id = sha256("demo-verification-key:" + circuit_hash)
    proof_hash = compute_proof_hash(
        circuit_hash=circuit_hash,
        proof_bytes=proof_bytes,
        public_inputs=public_inputs,
        proof_system=proof_system,
        trace_hash=trace_hash,
    )

    computation = (
        ComputationBuilder()
        .set_circuit_id(circuit_id)
        .set_circuit_version(circuit_version)
        .set_circuit_hash(circuit_hash)
        .set_input_hash(input_hash)
        .set_output_hash(output_hash)
        .set_trace_hash(trace_hash)
        .set_integrity_hash(integrity_hash)
        .build()
    )

    proof = (
        ProofBuilder()
        .set_proof_system(proof_system)
        .set_proof_bytes(proof_bytes)
        .set_public_inputs(public_inputs)
        .set_verification_key_id(verification_key_id)
        .set_proof_hash(proof_hash)
        .build()
    )

    bundle = (
        ProofBundleBuilder()
        .set_ai_identity(ai_identity)
        .set_computation(computation)
        .set_proof(proof)
        .set_issued_at("2026-04-05T00:00:00.000Z")
        .set_bundle_id(compute_bundle_id_from_integrity(integrity_hash))
        .build()
    )

    OUTPUT_PATH.write_text(bundle.to_json(pretty=True), encoding="utf-8")

    verifier = Verifier()
    result = verifier.verify(bundle)

    summary = {
        "output_path": str(OUTPUT_PATH),
        "bundle_id": bundle.bundle_id,
        "ai_id": ai_identity.ai_id,
        "integrity_hash": integrity_hash,
        "proof_hash": proof_hash,
        "is_valid": result.is_valid,
        "status": result.status.value,
    }
    print(json.dumps(summary, indent=2))
    return 0 if result.is_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
