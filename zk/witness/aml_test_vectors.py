"""Test vectors for AML sanctions screening witness generation."""
from __future__ import annotations

from typing import Any


def get_test_vectors() -> list[dict[str, Any]]:
    """Return 3 test vectors: cleared name, flagged name, edge case (empty name)."""
    return [
        {
            'name': 'cleared_name_standard',
            'input': {
                'name': 'John Smith',
                'name_normalized': 'john smith',
                'sanctions_root': '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
                'screening_timestamp': '2026-04-04T12:00:00Z',
                'expected_result': 0,
            },
            'expected_output': {
                'screening_result': 0,
                'cleared': True,
            },
        },
        {
            'name': 'flagged_name_sanctions_hit',
            'input': {
                'name': 'Osama Bin Laden',
                'name_normalized': 'osama bin laden',
                'sanctions_root': '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
                'screening_timestamp': '2026-04-04T12:00:00Z',
                'expected_result': 1,
            },
            'expected_output': {
                'screening_result': 1,
                'cleared': False,
            },
        },
        {
            'name': 'edge_case_empty_name',
            'input': {
                'name': '',
                'name_normalized': '',
                'sanctions_root': '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
                'screening_timestamp': '2026-04-04T12:00:00Z',
                'expected_result': 0,
            },
            'expected_output': {
                'screening_result': 0,
                'cleared': True,
            },
        },
    ]
