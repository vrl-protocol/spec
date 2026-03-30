from __future__ import annotations

from utils.hashing import constant_time_equal, sha256_hex


def test_constant_time_equal_matches_identical_hashes() -> None:
    digest = sha256_hex('verifiable-reality-layer')
    assert constant_time_equal(digest, digest)
