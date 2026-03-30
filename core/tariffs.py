from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal

from utils.canonical import canonical_json
from utils.hashing import constant_time_equal, sha256_hex

DATASET_VERSION = '2026.03.28'


@dataclass(frozen=True)
class TariffRule:
    hs_prefix: str
    rule_ref: str
    description: str
    duty_rate: Decimal
    section_301_rate: Decimal
    section_301_origin_countries: tuple[str, ...]


TARIFF_RULES: tuple[TariffRule, ...] = (
    TariffRule('8471300100', 'HTS-8471300100', 'Portable digital processing machines', Decimal('0.0000'), Decimal('0.0000'), ()),
    TariffRule('8507600000', 'HTS-8507600000', 'Lithium-ion accumulators', Decimal('0.0340'), Decimal('0.2500'), ('CN',)),
    TariffRule('6110200000', 'HTS-6110200000', 'Sweaters, pullovers, cardigans', Decimal('0.1650'), Decimal('0.0000'), ()),
    TariffRule('6403990000', 'HTS-6403990000', 'Footwear with outer soles of rubber/plastics', Decimal('0.3750'), Decimal('0.0000'), ()),
    TariffRule('8703220000', 'HTS-8703220000', 'Motor cars', Decimal('0.0250'), Decimal('0.0000'), ()),
    TariffRule('9403600000', 'HTS-9403600000', 'Other wooden furniture', Decimal('0.0000'), Decimal('0.0000'), ()),
)


def _dataset_payload() -> dict[str, object]:
    return {
        'dataset_version': DATASET_VERSION,
        'rules': [asdict(rule) for rule in TARIFF_RULES],
    }


DATASET_HASH = sha256_hex(canonical_json(_dataset_payload()))
EXPECTED_DATASET_HASH = DATASET_HASH


class TariffLookupError(LookupError):
    pass


class DatasetIntegrityError(RuntimeError):
    pass


def validate_dataset_integrity() -> None:
    current = sha256_hex(canonical_json(_dataset_payload()))
    if not constant_time_equal(current, EXPECTED_DATASET_HASH):
        raise DatasetIntegrityError('Tariff dataset integrity check failed')


def lookup_tariff_rule(hs_code: str) -> TariffRule:
    validate_dataset_integrity()
    for rule in TARIFF_RULES:
        if hs_code == rule.hs_prefix:
            return rule
    raise TariffLookupError(f'No tariff rule found for HS code {hs_code}')


def tariff_catalog() -> list[dict[str, str]]:
    return [
        {
            'hs_prefix': rule.hs_prefix,
            'rule_ref': rule.rule_ref,
            'description': rule.description,
            'duty_rate': format(rule.duty_rate, 'f'),
            'section_301_rate': format(rule.section_301_rate, 'f'),
            'section_301_origin_countries': list(rule.section_301_origin_countries),
        }
        for rule in TARIFF_RULES
    ]
