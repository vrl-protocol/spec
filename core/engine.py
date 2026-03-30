from __future__ import annotations

from decimal import Decimal
from typing import Any

from core.proof import build_proof_artifact
from core.tariffs import DATASET_HASH, DATASET_VERSION, lookup_tariff_rule
from models.schemas import CalculationResponse, CalculationResult, ImportCalculationRequest, TraceStep
from utils.canonical import canonical_json
from utils.decimal import clamp_money, money, rate
from utils.hashing import sha256_hex

MPF_RATE = rate("0.003464")
MPF_MIN = money("32.71")
MPF_MAX = money("634.62")
HMF_RATE = rate("0.00125")


def _decimal_string(value: Decimal) -> str:
    return format(value, "f")


def _make_step(step: str, rule_ref: str, inputs: dict[str, Any], outputs: dict[str, Any]) -> TraceStep:
    normalized_inputs = {key: _decimal_string(value) if isinstance(value, Decimal) else str(value) for key, value in inputs.items()}
    normalized_outputs = {key: _decimal_string(value) if isinstance(value, Decimal) else str(value) for key, value in outputs.items()}
    return TraceStep(step=step, rule_ref=rule_ref, inputs=normalized_inputs, outputs=normalized_outputs)


def calculate_import_landed_cost(request: ImportCalculationRequest) -> CalculationResponse:
    validated_request = ImportCalculationRequest.model_validate(request.model_dump(mode="python"))
    request_payload = validated_request.model_dump(mode="python")
    request_hash = sha256_hex(canonical_json(request_payload))

    tariff_rule = lookup_tariff_rule(validated_request.hs_code)
    extended_customs_value = money(validated_request.customs_value * validated_request.quantity)
    duty_amount = money(extended_customs_value * tariff_rule.duty_rate)
    section_301_amount = money(extended_customs_value * tariff_rule.section_301_rate) if validated_request.country_of_origin in tariff_rule.section_301_origin_countries else money("0")
    mpf_amount = clamp_money(extended_customs_value * MPF_RATE, minimum=MPF_MIN, maximum=MPF_MAX)
    hmf_amount = money(extended_customs_value * HMF_RATE) if validated_request.shipping_mode == "ocean" else money("0")
    landed_cost = money(
        extended_customs_value
        + validated_request.freight
        + validated_request.insurance
        + duty_amount
        + section_301_amount
        + mpf_amount
        + hmf_amount
    )

    trace = [
        _make_step(
            "canonical_input",
            "INPUT-CANON",
            request_payload,
            {
                "input_hash": request_hash,
                "dataset_version": DATASET_VERSION,
                "dataset_hash": DATASET_HASH,
            },
        ),
        _make_step(
            "tariff_lookup",
            tariff_rule.rule_ref,
            {"hs_code": validated_request.hs_code, "country_of_origin": validated_request.country_of_origin},
            {
                "rule_ref": tariff_rule.rule_ref,
                "description": tariff_rule.description,
                "duty_rate": tariff_rule.duty_rate,
                "section_301_rate": tariff_rule.section_301_rate,
            },
        ),
        _make_step(
            "extended_customs_value",
            tariff_rule.rule_ref,
            {"unit_customs_value": validated_request.customs_value, "quantity": validated_request.quantity},
            {"extended_customs_value": extended_customs_value},
        ),
        _make_step(
            "base_duty",
            tariff_rule.rule_ref,
            {"extended_customs_value": extended_customs_value, "duty_rate": tariff_rule.duty_rate},
            {"duty_amount": duty_amount},
        ),
        _make_step(
            "section_301",
            tariff_rule.rule_ref,
            {"extended_customs_value": extended_customs_value, "country_of_origin": validated_request.country_of_origin},
            {"section_301_amount": section_301_amount},
        ),
        _make_step(
            "mpf",
            "MPF-2026",
            {"extended_customs_value": extended_customs_value, "mpf_rate": MPF_RATE, "minimum": MPF_MIN, "maximum": MPF_MAX},
            {"mpf_amount": mpf_amount},
        ),
        _make_step(
            "hmf",
            "HMF-2026",
            {"extended_customs_value": extended_customs_value, "shipping_mode": validated_request.shipping_mode},
            {"hmf_amount": hmf_amount},
        ),
        _make_step(
            "landed_cost",
            "LC-2026",
            {
                "extended_customs_value": extended_customs_value,
                "freight": validated_request.freight,
                "insurance": validated_request.insurance,
                "duty_amount": duty_amount,
                "section_301_amount": section_301_amount,
                "mpf_amount": mpf_amount,
                "hmf_amount": hmf_amount,
            },
            {"landed_cost": landed_cost},
        ),
    ]

    result = CalculationResult(
        dataset_version=DATASET_VERSION,
        dataset_hash=DATASET_HASH,
        hs_code=validated_request.hs_code,
        country_of_origin=validated_request.country_of_origin,
        quantity=validated_request.quantity,
        tariff_rule_ref=tariff_rule.rule_ref,
        tariff_description=tariff_rule.description,
        unit_customs_value=money(validated_request.customs_value),
        extended_customs_value=extended_customs_value,
        freight=money(validated_request.freight),
        insurance=money(validated_request.insurance),
        duty_rate=rate(tariff_rule.duty_rate),
        section_301_rate=rate(tariff_rule.section_301_rate),
        duty_amount=duty_amount,
        section_301_amount=section_301_amount,
        mpf_amount=mpf_amount,
        hmf_amount=hmf_amount,
        landed_cost=landed_cost,
    )

    proof = build_proof_artifact(request_payload, result.model_dump(mode="python"), [step.model_dump(mode="python") for step in trace])
    return CalculationResponse(result=result, trace=trace, proof=proof)
