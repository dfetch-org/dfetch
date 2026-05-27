"""Property-based fuzz tests for dfetch's pure string/parser helpers.

Where ``test_fuzzing.py`` fuzzes the manifest and the ``check``/``update``
commands end-to-end, this module fuzzes the small, deterministic parsing and
transformation functions that process untrusted input (version strings, VCS
URLs, integrity hashes, SSH commands, archive names, glob prefixes). Each test
asserts a *property* that must hold for every input rather than merely checking
that no exception is raised.
"""

# mypy: ignore-errors

from __future__ import annotations

import os
import tempfile

from hypothesis import given, settings
from hypothesis import strategies as st
from packageurl import PackageURL

from dfetch.util.purl import vcs_url_to_purl
from dfetch.util.ssh import InvalidSshCommandError, sanitize_ssh_cmd
from dfetch.util.util import (
    always_str_list,
    check_no_path_traversal,
    str_if_possible,
    strip_glob_prefix,
)
from dfetch.util.versions import (
    coerce,
    is_commit_sha,
    latest_tag_from_list,
    prioritise_default,
    sort_tags_newest_first,
)
from dfetch.vcs.archive import (
    ARCHIVE_EXTENSIONS,
    is_archive_url,
    strip_archive_extension,
)
from dfetch.vcs.integrity_hash import (
    SUPPORTED_HASH_ALGORITHMS,
    IntegrityHash,
)

MAX_EXAMPLES = 50 if os.getenv("CI") else 200

# Arbitrary text, but without surrogates/NUL so it can round-trip through
# subprocess-style code paths and the filesystem during testing.
TEXT = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\x00"),
    max_size=64,
)
HEX = st.text(alphabet="0123456789abcdefABCDEF", max_size=128)


# --------------------------------------------------------------------------- #
# dfetch.vcs.integrity_hash
# --------------------------------------------------------------------------- #
@settings(max_examples=MAX_EXAMPLES, deadline=None)
@given(st.sampled_from(SUPPORTED_HASH_ALGORITHMS), HEX)
def test_integrity_hash_parse_roundtrips(algo, hex_digest):
    """A ``<algo>:<hex>`` string parses back into its parts and re-serialises."""
    parsed = IntegrityHash.parse(f"{algo}:{hex_digest}")
    assert parsed is not None
    assert parsed.algorithm == algo
    assert parsed.hex_digest == hex_digest
    assert str(parsed) == f"{algo}:{hex_digest}"


@settings(max_examples=MAX_EXAMPLES, deadline=None)
@given(TEXT)
def test_integrity_hash_parse_never_raises(value):
    """Parsing arbitrary text returns either ``None`` or an :class:`IntegrityHash`."""
    result = IntegrityHash.parse(value)
    assert result is None or isinstance(result, IntegrityHash)


@settings(max_examples=MAX_EXAMPLES, deadline=None)
@given(st.sampled_from(SUPPORTED_HASH_ALGORITHMS), HEX)
def test_integrity_hash_matches_is_case_insensitive(algo, hex_digest):
    """A digest matches itself regardless of letter case."""
    integrity = IntegrityHash(algo, hex_digest)
    assert integrity.matches(hex_digest)
    assert integrity.matches(hex_digest.upper())
    assert integrity.matches(hex_digest.lower())


# --------------------------------------------------------------------------- #
# dfetch.util.versions
# --------------------------------------------------------------------------- #
@settings(max_examples=MAX_EXAMPLES, deadline=None)
@given(TEXT)
def test_coerce_partitions_the_input(value):
    """``coerce`` splits the string into prefix + match + rest without loss."""
    prefix, version, rest = coerce(value)
    assert value.startswith(prefix)
    assert value.endswith(rest)
    assert len(prefix) + len(rest) <= len(value)
    if version is None:
        # No version found: nothing is consumed, the whole string is the rest.
        assert prefix == ""
        assert rest == value


# VCS branch and tag names are unique within a repository.
UNIQUE_REFS = st.lists(TEXT, max_size=8, unique=True)


@settings(max_examples=MAX_EXAMPLES, deadline=None)
@given(UNIQUE_REFS, TEXT)
def test_prioritise_default_is_a_reordering(branches, default):
    """The default branch is moved first and no branch is added or dropped."""
    result = prioritise_default(branches, default)
    assert sorted(result) == sorted(branches)
    if default in branches:
        assert result[0] == default


@settings(max_examples=MAX_EXAMPLES, deadline=None)
@given(UNIQUE_REFS)
def test_sort_tags_is_a_permutation(tags):
    """Sorting tags never gains, loses, or mutates a tag."""
    assert sorted(sort_tags_newest_first(tags)) == sorted(tags)


@settings(max_examples=MAX_EXAMPLES, deadline=None)
@given(TEXT)
def test_is_commit_sha_matches_definition(value):
    """``is_commit_sha`` is true exactly for 7-40 char hex strings."""
    expected = 7 <= len(value) <= 40 and all(
        c in "0123456789abcdefABCDEF" for c in value
    )
    assert is_commit_sha(value) == expected


@settings(max_examples=MAX_EXAMPLES, deadline=None)
@given(TEXT, st.lists(TEXT, max_size=8))
def test_latest_tag_is_a_known_tag(current, available):
    """The selected latest tag is always the current tag or one that exists."""
    result = latest_tag_from_list(current, available)
    assert result == current or result in available


# --------------------------------------------------------------------------- #
# dfetch.vcs.archive
# --------------------------------------------------------------------------- #
# A bare filename stem: no URL query (?)/fragment (#)/path (/) separators.
STEM = st.text(
    alphabet=st.characters(
        whitelist_categories=("Ll", "Lu", "Nd"),
        whitelist_characters="-_.",
    ),
    min_size=1,
    max_size=20,
)


@settings(max_examples=MAX_EXAMPLES, deadline=None)
@given(STEM, st.sampled_from(ARCHIVE_EXTENSIONS))
def test_archive_extension_detected_and_stripped(stem, ext):
    """A URL whose path ends in a known extension is detected and stripped."""
    url = f"https://example.com/{stem}{ext}"
    assert is_archive_url(url)
    name = f"{stem}{ext}"
    assert strip_archive_extension(name) == name[: -len(ext)]


@settings(max_examples=MAX_EXAMPLES, deadline=None)
@given(TEXT)
def test_archive_helpers_never_raise(value):
    """Detection/stripping return well-typed results for arbitrary input."""
    assert isinstance(is_archive_url(value), bool)
    assert isinstance(strip_archive_extension(value), str)


# --------------------------------------------------------------------------- #
# dfetch.util.ssh
# --------------------------------------------------------------------------- #
@settings(max_examples=MAX_EXAMPLES, deadline=None)
@given(TEXT)
def test_sanitize_ssh_only_raises_its_own_error(value):
    """The allowlist either returns a string or raises InvalidSshCommandError."""
    try:
        result = sanitize_ssh_cmd(value)
    except InvalidSshCommandError:
        return
    assert isinstance(result, str)
    # Anything accepted must be accepted again unchanged (idempotent).
    assert sanitize_ssh_cmd(result) == result


# --------------------------------------------------------------------------- #
# dfetch.util.purl
# --------------------------------------------------------------------------- #
@settings(max_examples=MAX_EXAMPLES, deadline=None)
@given(TEXT, st.none() | TEXT)
def test_vcs_url_to_purl_always_builds_a_purl(url, version):
    """Any URL-ish string converts to a PackageURL without crashing."""
    assert isinstance(vcs_url_to_purl(url, version=version), PackageURL)


# --------------------------------------------------------------------------- #
# dfetch.util.util list helpers and glob/path handling
# --------------------------------------------------------------------------- #
@settings(max_examples=MAX_EXAMPLES, deadline=None)
@given(st.lists(TEXT.filter(lambda s: s != ""), max_size=8))
def test_str_list_roundtrip(items):
    """``always_str_list`` inverts ``str_if_possible`` for non-empty entries."""
    assert always_str_list(str_if_possible(items)) == items


@settings(max_examples=MAX_EXAMPLES, deadline=None)
@given(TEXT, TEXT)
def test_strip_glob_prefix_never_raises(path, pattern):
    """Stripping a glob prefix always yields a string."""
    assert isinstance(strip_glob_prefix(path, pattern), str)


PATH_COMPONENT = st.text(
    alphabet=st.characters(
        whitelist_categories=("Ll", "Lu", "Nd"),
        whitelist_characters="-_",
    ),
    min_size=1,
    max_size=12,
)


@settings(max_examples=MAX_EXAMPLES, deadline=None)
@given(st.lists(PATH_COMPONENT, min_size=1, max_size=5))
def test_path_within_root_is_allowed(parts):
    """A path built from plain components under the root never escapes it."""
    with tempfile.TemporaryDirectory() as root:
        check_no_path_traversal(os.path.join(root, *parts), root)


@settings(max_examples=MAX_EXAMPLES, deadline=None)
@given(st.integers(min_value=1, max_value=6), st.lists(PATH_COMPONENT, max_size=3))
def test_dotdot_escape_is_rejected(depth, tail):
    """Climbing above the root with ``..`` components is always rejected."""
    with tempfile.TemporaryDirectory() as root:
        nested = os.path.join(root, "sub")
        escaping = os.path.join(nested, *([".."] * depth), *tail)
        try:
            check_no_path_traversal(escaping, nested)
        except RuntimeError:
            return
        # No error only if the path stayed within `nested` after resolution.
        assert os.path.realpath(escaping).startswith(os.path.realpath(nested))
