"""Unit tests for dfetch.vcs.integrity_hash."""

import pytest

from dfetch.vcs.integrity_hash import SUPPORTED_HASH_ALGORITHMS, IntegrityHash

# ---------------------------------------------------------------------------
# SUPPORTED_HASH_ALGORITHMS
# ---------------------------------------------------------------------------


def test_supported_hash_algorithms_contains_sha256():
    assert "sha256" in SUPPORTED_HASH_ALGORITHMS


def test_supported_hash_algorithms_contains_sha384():
    assert "sha384" in SUPPORTED_HASH_ALGORITHMS


def test_supported_hash_algorithms_contains_sha512():
    assert "sha512" in SUPPORTED_HASH_ALGORITHMS


# ---------------------------------------------------------------------------
# IntegrityHash.parse
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value,expected_algo,expected_hex",
    [
        ("sha256:abc123", "sha256", "abc123"),
        ("sha384:def456", "sha384", "def456"),
        ("sha512:ghi789", "sha512", "ghi789"),
    ],
)
def test_parse_valid(value, expected_algo, expected_hex):
    h = IntegrityHash.parse(value)
    assert h is not None
    assert h.algorithm == expected_algo
    assert h.hex_digest == expected_hex


def test_parse_returns_none_for_url():
    assert IntegrityHash.parse("https://example.com/lib.tar.gz") is None


def test_parse_returns_none_for_plain_string():
    assert IntegrityHash.parse("notahash") is None


# ---------------------------------------------------------------------------
# IntegrityHash.__str__ / __repr__
# ---------------------------------------------------------------------------


def test_str_roundtrip():
    h = IntegrityHash("sha256", "abc123")
    assert str(h) == "sha256:abc123"


def test_repr():
    h = IntegrityHash("sha256", "abc123")
    assert repr(h) == "IntegrityHash('sha256', 'abc123')"


# ---------------------------------------------------------------------------
# IntegrityHash.__eq__ / __hash__
# ---------------------------------------------------------------------------


def test_eq_same():
    assert IntegrityHash("sha256", "abc") == IntegrityHash("sha256", "abc")


def test_eq_case_insensitive_hex():
    assert IntegrityHash("sha256", "ABCDEF") == IntegrityHash("sha256", "abcdef")


def test_eq_different_digest():
    assert IntegrityHash("sha256", "aaa") != IntegrityHash("sha256", "bbb")


def test_eq_non_integrity_hash_returns_not_implemented():
    assert IntegrityHash("sha256", "abc").__eq__("sha256:abc") is NotImplemented


def test_hash_usable_in_set():
    a = IntegrityHash("sha256", "abc")
    b = IntegrityHash("sha256", "ABC")
    assert len({a, b}) == 1


# ---------------------------------------------------------------------------
# IntegrityHash.matches
# ---------------------------------------------------------------------------


def test_matches_equal():
    h = IntegrityHash("sha256", "a" * 64)
    assert h.matches("a" * 64) is True


def test_matches_case_insensitive():
    h = IntegrityHash("sha256", "abcdef")
    assert h.matches("ABCDEF") is True


def test_matches_not_equal():
    h = IntegrityHash("sha256", "a" * 64)
    assert h.matches("b" * 64) is False
