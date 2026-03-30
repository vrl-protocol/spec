from __future__ import annotations

import json
from pathlib import Path

from backend.proof_export import export_proof_bundle, verify_proof_bundle

REFERENCE_VECTOR = Path(__file__).resolve().parent / 'reference_vector.json'


def test_reference_vector_is_reproducible():
  vector = json.loads(REFERENCE_VECTOR.read_text(encoding='utf-8'))
  bundle_a = export_proof_bundle(vector['input'])
  bundle_b = export_proof_bundle(vector['input'])
  expected = vector['expected']

  assert bundle_a['input_hash'] == bundle_b['input_hash']
  assert bundle_a['trace_hash'] == bundle_b['trace_hash']
  assert bundle_a['circuit_hash'] == bundle_b['circuit_hash']
  assert bundle_a['verification_key_hash'] == bundle_b['verification_key_hash']
  assert bundle_a['proof']['proof_blob_hex'] == bundle_b['proof']['proof_blob_hex']
  assert bundle_a['proof']['final_proof'] == bundle_b['proof']['final_proof']
  assert bundle_a['input_hash'] == expected['input_hash']
  assert bundle_a['output_hash'] == expected['output_hash']
  assert bundle_a['trace_hash'] == expected['trace_hash']
  assert bundle_a['circuit_hash'] == expected['circuit_hash']
  assert bundle_a['verification_key_hash'] == expected['verification_key_hash']
  assert bundle_a['proof']['final_proof'] == expected['final_proof']


def test_exported_bundle_verifies_offline():
  vector = json.loads(REFERENCE_VECTOR.read_text(encoding='utf-8'))
  bundle = export_proof_bundle(vector['input'])
  result = verify_proof_bundle(bundle)
  assert result['valid'] is True
