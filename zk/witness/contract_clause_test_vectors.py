"""Test vectors for contract clause classification witness generation."""
from __future__ import annotations

from utils.hashing import sha256_hex
from zk.witness.contract_clause_witness_generator import (
    ContractClauseWitnessInput,
    build_contract_clause_assignment,
)


def test_vector_gdpr_special_category_high_risk() -> tuple[ContractClauseWitnessInput, dict[str, object]]:
    """
    Test vector 1: GDPR special category data (HIGH_RISK).
    Clause discusses processing of health/genetic data without explicit safeguards.
    """
    clause_text = (
        'The Processor may collect, store, and process health information, genetic data, '
        'and medical history as part of the service without explicit user consent per record.'
    )
    clause_id = 'CLAUSE_GDPR_ART9_001'
    model_raw_output = (
        'CLASSIFICATION: HIGH_RISK | REASONING: Clause involves special category data (health, genetic) '
        'under GDPR Article 9. Processing without explicit consent per record is prohibited.'
    )
    classification_result = 'HIGH_RISK'
    ruleset_id_hash = sha256_hex('GDPR_ARTICLE_9_SPECIAL_CATEGORY_DATA_RULESET')
    ai_id = sha256_hex('gpt-4-legal-classifier-v2.1')
    audit_entry_hash = sha256_hex('AUDIT_2026-04-04_GDPR_CLASSIFICATION_001')

    witness_input = ContractClauseWitnessInput(
        clause_text=clause_text,
        clause_id=clause_id,
        model_raw_output=model_raw_output,
        classification_result=classification_result,
        ruleset_id_hash=ruleset_id_hash,
        ai_id=ai_id,
        audit_entry_hash=audit_entry_hash,
    )

    assignment = build_contract_clause_assignment(witness_input)
    assert assignment.verify_gate_constraints() == [True] * 7, 'Gate constraints failed for HIGH_RISK vector'

    return witness_input, {
        'vector_name': 'GDPR Special Category (HIGH_RISK)',
        'classification': 'HIGH_RISK',
        'encoding_value': 3,
        'gate_count': 7,
        'all_gates_valid': all(assignment.verify_gate_constraints()),
    }


def test_vector_commercial_term_compliant() -> tuple[ContractClauseWitnessInput, dict[str, object]]:
    """
    Test vector 2: Standard commercial term (COMPLIANT).
    Clause discusses general service availability and SLA terms.
    """
    clause_text = (
        'The Service is provided on an as-is basis with 99.5% uptime SLA. '
        'Standard maintenance windows are excluded from SLA calculations.'
    )
    clause_id = 'CLAUSE_SLA_COMMERCIAL_001'
    model_raw_output = (
        'CLASSIFICATION: COMPLIANT | REASONING: Clause contains standard SLA and service terms '
        'that are commonly accepted and do not trigger compliance risks.'
    )
    classification_result = 'COMPLIANT'
    ruleset_id_hash = sha256_hex('COMMERCIAL_TERMS_RULESET')
    ai_id = sha256_hex('gpt-4-legal-classifier-v2.1')
    audit_entry_hash = sha256_hex('AUDIT_2026-04-04_COMMERCIAL_CLASSIFICATION_001')

    witness_input = ContractClauseWitnessInput(
        clause_text=clause_text,
        clause_id=clause_id,
        model_raw_output=model_raw_output,
        classification_result=classification_result,
        ruleset_id_hash=ruleset_id_hash,
        ai_id=ai_id,
        audit_entry_hash=audit_entry_hash,
    )

    assignment = build_contract_clause_assignment(witness_input)
    assert assignment.verify_gate_constraints() == [True] * 7, 'Gate constraints failed for COMPLIANT vector'

    return witness_input, {
        'vector_name': 'Commercial SLA Term (COMPLIANT)',
        'classification': 'COMPLIANT',
        'encoding_value': 0,
        'gate_count': 7,
        'all_gates_valid': all(assignment.verify_gate_constraints()),
    }


def test_vector_data_sharing_medium_risk() -> tuple[ContractClauseWitnessInput, dict[str, object]]:
    """
    Test vector 3: Ambiguous data sharing clause (MEDIUM_RISK).
    Clause discusses sharing with third parties but with some safeguards.
    """
    clause_text = (
        'The Processor may share pseudonymized data with selected third-party partners '
        'for analytics and research purposes. Data sharing partners must execute a DPA, '
        'but the specific safeguards for re-identification risk are not detailed.'
    )
    clause_id = 'CLAUSE_DATA_SHARING_003'
    model_raw_output = (
        'CLASSIFICATION: MEDIUM_RISK | REASONING: Clause permits third-party data sharing with DPA requirement '
        'but lacks specificity on re-identification safeguards and audit controls. '
        'Requires clarification for full compliance.'
    )
    classification_result = 'MEDIUM_RISK'
    ruleset_id_hash = sha256_hex('DATA_SHARING_AND_THIRD_PARTY_RULESET')
    ai_id = sha256_hex('gpt-4-legal-classifier-v2.1')
    audit_entry_hash = sha256_hex('AUDIT_2026-04-04_DATA_SHARING_CLASSIFICATION_001')

    witness_input = ContractClauseWitnessInput(
        clause_text=clause_text,
        clause_id=clause_id,
        model_raw_output=model_raw_output,
        classification_result=classification_result,
        ruleset_id_hash=ruleset_id_hash,
        ai_id=ai_id,
        audit_entry_hash=audit_entry_hash,
    )

    assignment = build_contract_clause_assignment(witness_input)
    assert assignment.verify_gate_constraints() == [True] * 7, 'Gate constraints failed for MEDIUM_RISK vector'

    return witness_input, {
        'vector_name': 'Ambiguous Data Sharing (MEDIUM_RISK)',
        'classification': 'MEDIUM_RISK',
        'encoding_value': 2,
        'gate_count': 7,
        'all_gates_valid': all(assignment.verify_gate_constraints()),
    }


def generate_all_test_vectors() -> list[tuple[ContractClauseWitnessInput, dict[str, object]]]:
    """Generate all three test vectors."""
    return [
        test_vector_gdpr_special_category_high_risk(),
        test_vector_commercial_term_compliant(),
        test_vector_data_sharing_medium_risk(),
    ]
