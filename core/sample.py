from __future__ import annotations

from decimal import Decimal

REFERENCE_REQUEST = {
    'hs_code': '8507600000',
    'country_of_origin': 'CN',
    'customs_value': Decimal('1200.00'),
    'freight': Decimal('150.00'),
    'insurance': Decimal('25.00'),
    'quantity': 2,
    'shipping_mode': 'ocean',
}
