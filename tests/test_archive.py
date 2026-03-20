"""Unit tests for dfetch.vcs.archive."""

import io
import os
import tarfile
import tempfile
import zipfile

import pytest

import dfetch.project  # noqa: F401 – must be imported before dfetch.vcs.archive to break circular init
from dfetch.vcs.archive import (
    ARCHIVE_EXTENSIONS,
    SUPPORTED_HASH_ALGORITHMS,
    ArchiveLocalRepo,
    ArchiveRemote,
    _safe_compare_hex,
    _suffix_for_url,
    compute_hash,
    is_archive_url,
)

# These are static methods on ArchiveLocalRepo
_check_archive_limits = ArchiveLocalRepo._check_archive_limits
_check_zip_members = ArchiveLocalRepo._check_zip_members
_check_tar_members = ArchiveLocalRepo._check_tar_members


# ---------------------------------------------------------------------------
# compute_hash
# ---------------------------------------------------------------------------


def test_compute_hash_empty_file():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        path = f.name
    try:
        digest = compute_hash(path, "sha256")
        # SHA-256 of empty string
        assert digest == "e3b0c44298fc1c149afbf4c8996fb924" "27ae41e4649b934ca495991b7852b855"
    finally:
        os.remove(path)


def test_compute_hash_known_content():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"hello world\n")
        path = f.name
    try:
        digest = compute_hash(path, "sha256")
        assert len(digest) == 64
        assert all(c in "0123456789abcdef" for c in digest)
    finally:
        os.remove(path)


def test_compute_hash_unsupported_algorithm():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        path = f.name
    try:
        with pytest.raises(RuntimeError, match="Unsupported hash algorithm"):
            compute_hash(path, "md5")
    finally:
        os.remove(path)


def test_compute_hash_default_is_sha256():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"data")
        path = f.name
    try:
        digest = compute_hash(path)
        assert len(digest) == 64
    finally:
        os.remove(path)


# ---------------------------------------------------------------------------
# _safe_compare_hex
# ---------------------------------------------------------------------------


def test_safe_compare_hex_equal():
    h = "a" * 64
    assert _safe_compare_hex(h, h) is True


def test_safe_compare_hex_case_insensitive():
    assert _safe_compare_hex("ABCDEF", "abcdef") is True


def test_safe_compare_hex_not_equal():
    assert _safe_compare_hex("a" * 64, "b" * 64) is False


# ---------------------------------------------------------------------------
# is_archive_url
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/lib.tar.gz",
        "https://example.com/lib.tgz",
        "https://example.com/lib.tar.bz2",
        "https://example.com/lib.tar.xz",
        "https://example.com/lib.zip",
        "file:///tmp/lib.ZIP",  # case-insensitive
    ],
)
def test_is_archive_url_true(url):
    assert is_archive_url(url) is True


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/repo.git",
        "https://example.com/",
        "svn://svn.example.com/trunk",
        "https://example.com/lib.tar.gz.sig",
    ],
)
def test_is_archive_url_false(url):
    assert is_archive_url(url) is False


# ---------------------------------------------------------------------------
# _suffix_for_url
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://example.com/lib.tar.gz", ".tar.gz"),
        ("https://example.com/lib.tgz", ".tgz"),
        ("https://example.com/lib.tar.bz2", ".tar.bz2"),
        ("https://example.com/lib.tar.xz", ".tar.xz"),
        ("https://example.com/lib.zip", ".zip"),
        ("https://example.com/lib.unknown", ".archive"),
    ],
)
def test_suffix_for_url(url, expected):
    assert _suffix_for_url(url) == expected


def test_suffix_for_url_prefers_longest_match():
    # .tar.gz should win over .gz
    assert _suffix_for_url("https://example.com/lib.tar.gz") == ".tar.gz"


# ---------------------------------------------------------------------------
# _check_archive_limits
# ---------------------------------------------------------------------------


def test_check_archive_limits_ok():
    _check_archive_limits(member_count=1, total_bytes=1024)  # should not raise


def test_check_archive_limits_too_many_members():
    with pytest.raises(RuntimeError, match="safety limit"):
        _check_archive_limits(member_count=10_001, total_bytes=0)


def test_check_archive_limits_too_large():
    with pytest.raises(RuntimeError, match="safety limit"):
        _check_archive_limits(member_count=1, total_bytes=500 * 1024 * 1024 + 1)


# ---------------------------------------------------------------------------
# _check_zip_members
# ---------------------------------------------------------------------------


def _make_zip(member_names: list[str]) -> zipfile.ZipFile:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name in member_names:
            zf.writestr(name, "content")
    buf.seek(0)
    return zipfile.ZipFile(buf)


def test_check_zip_members_safe():
    zf = _make_zip(["project/README.md", "project/src/main.c"])
    _check_zip_members(zf)  # should not raise


def test_check_zip_members_dot_dot():
    zf = _make_zip(["project/../etc/passwd"])
    with pytest.raises(RuntimeError, match="unsafe member path"):
        _check_zip_members(zf)


def test_check_zip_members_absolute():
    zf = _make_zip(["/etc/passwd"])
    with pytest.raises(RuntimeError, match="unsafe member path"):
        _check_zip_members(zf)


# ---------------------------------------------------------------------------
# _check_tar_members
# ---------------------------------------------------------------------------


def _make_tar(member_names: list[str]) -> tarfile.TarFile:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for name in member_names:
            content = b"content"
            info = tarfile.TarInfo(name=name)
            info.size = len(content)
            tf.addfile(info, io.BytesIO(content))
    buf.seek(0)
    return tarfile.open(fileobj=buf, mode="r:gz")


def test_check_tar_members_safe():
    tf = _make_tar(["project/README.md", "project/src/main.c"])
    _check_tar_members(tf)  # should not raise


def test_check_tar_members_dot_dot():
    tf = _make_tar(["project/../etc/passwd"])
    with pytest.raises(RuntimeError, match="unsafe member path"):
        _check_tar_members(tf)


def test_check_tar_members_absolute():
    tf = _make_tar(["/etc/passwd"])
    with pytest.raises(RuntimeError, match="unsafe member path"):
        _check_tar_members(tf)


# ---------------------------------------------------------------------------
# ArchiveRemote.is_accessible
# ---------------------------------------------------------------------------


def test_is_accessible_existing_file():
    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as f:
        path = f.name
    try:
        url = f"file:///{path.lstrip('/')}"
        remote = ArchiveRemote(url)
        assert remote.is_accessible() is True
    finally:
        os.remove(path)


def test_is_accessible_missing_file():
    remote = ArchiveRemote("file:////nonexistent/path/lib.tar.gz")
    assert remote.is_accessible() is False


# ---------------------------------------------------------------------------
# ArchiveLocalRepo.extract – basic smoke test
# ---------------------------------------------------------------------------


def _make_tar_gz_file(archive_path: str, members: dict[str, bytes]) -> None:
    with tarfile.open(archive_path, "w:gz") as tf:
        for name, content in members.items():
            info = tarfile.TarInfo(name=name)
            info.size = len(content)
            tf.addfile(info, io.BytesIO(content))


def test_extract_tar_gz_strips_top_level_dir():
    with tempfile.TemporaryDirectory() as tmp:
        archive_path = os.path.join(tmp, "lib.tar.gz")
        _make_tar_gz_file(
            archive_path,
            {
                "lib-1.0/README.md": b"hello",
                "lib-1.0/src/main.c": b"int main(){}",
            },
        )
        dest = os.path.join(tmp, "dest")
        ArchiveLocalRepo.extract(archive_path, dest)
        assert os.path.isfile(os.path.join(dest, "README.md"))
        assert os.path.isfile(os.path.join(dest, "src", "main.c"))


def test_extract_tar_gz_with_src_filter():
    with tempfile.TemporaryDirectory() as tmp:
        archive_path = os.path.join(tmp, "lib.tar.gz")
        _make_tar_gz_file(
            archive_path,
            {
                "lib-1.0/README.md": b"readme",
                "lib-1.0/src/main.c": b"main",
                "lib-1.0/tests/test.c": b"test",
            },
        )
        dest = os.path.join(tmp, "dest")
        ArchiveLocalRepo.extract(archive_path, dest, src="src")
        assert os.path.isfile(os.path.join(dest, "main.c"))
        assert not os.path.exists(os.path.join(dest, "tests"))
        # License-like files are not present in this archive so no extra files expected


def test_extract_zip():
    with tempfile.TemporaryDirectory() as tmp:
        archive_path = os.path.join(tmp, "lib.zip")
        with zipfile.ZipFile(archive_path, "w") as zf:
            zf.writestr("lib-1.0/README.md", "hello")
            zf.writestr("lib-1.0/src/main.c", "int main(){}")
        dest = os.path.join(tmp, "dest")
        ArchiveLocalRepo.extract(archive_path, dest)
        assert os.path.isfile(os.path.join(dest, "README.md"))
        assert os.path.isfile(os.path.join(dest, "src", "main.c"))


def test_all_archive_extensions_covered():
    """Ensure ARCHIVE_EXTENSIONS is a non-empty tuple of dot-prefixed strings."""
    assert len(ARCHIVE_EXTENSIONS) > 0
    for ext in ARCHIVE_EXTENSIONS:
        assert ext.startswith(".")


def test_supported_hash_algorithms():
    assert "sha256" in SUPPORTED_HASH_ALGORITHMS
