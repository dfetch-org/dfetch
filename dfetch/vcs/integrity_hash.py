"""Integrity hash: a ``<algorithm>:<hex>`` content fingerprint."""

from __future__ import annotations

import hmac

#: Supported hash algorithms, ordered strongest-first so :meth:`IntegrityHash.parse`
#: matches the most specific prefix when algorithm names share a common prefix.
SUPPORTED_HASH_ALGORITHMS = ("sha512", "sha384", "sha256")


class IntegrityHash:
    """A parsed ``<algorithm>:<hex>`` integrity hash value.

    Use :meth:`parse` to build one from a raw string (returns *None* when the
    string does not match a known algorithm prefix).  Use the constructor when
    both parts are already known.

    >>> h = IntegrityHash.parse("sha256:abc123")
    >>> h.algorithm, h.hex_digest
    ('sha256', 'abc123')
    >>> str(h)
    'sha256:abc123'
    """

    def __init__(self, algorithm: str, hex_digest: str) -> None:
        """Create an IntegrityHash from known *algorithm* and *hex_digest*."""
        self.algorithm = algorithm
        self.hex_digest = hex_digest

    @classmethod
    def parse(cls, value: str) -> IntegrityHash | None:
        """Return an :class:`IntegrityHash` when *value* is ``<algo>:<hex>``.

        Returns *None* when *value* does not start with a known algorithm prefix.
        """
        for algo in SUPPORTED_HASH_ALGORITHMS:
            if value.startswith(f"{algo}:"):
                return cls(algo, value[len(algo) + 1 :])
        return None

    def __str__(self) -> str:
        """Return the canonical ``<algorithm>:<hex>`` string."""
        return f"{self.algorithm}:{self.hex_digest}"

    def __repr__(self) -> str:
        """Return a developer-readable representation."""
        return f"IntegrityHash({self.algorithm!r}, {self.hex_digest!r})"

    def __eq__(self, other: object) -> bool:
        """Compare two :class:`IntegrityHash` instances (case-insensitive hex)."""
        if isinstance(other, IntegrityHash):
            return (
                self.algorithm == other.algorithm
                and self.hex_digest.lower() == other.hex_digest.lower()
            )
        return NotImplemented

    def __hash__(self) -> int:
        """Hash based on algorithm and lower-cased hex digest."""
        return hash((self.algorithm, self.hex_digest.lower()))

    def matches(self, actual_hex: str) -> bool:
        """Return *True* when *actual_hex* equals this hash's digest.

        Uses :func:`hmac.compare_digest` for constant-time comparison to
        avoid leaking timing information about the expected value.
        """
        return hmac.compare_digest(actual_hex.lower(), self.hex_digest.lower())
