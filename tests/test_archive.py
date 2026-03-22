"""Unit tests for dfetch.vcs.archive and dfetch.project.archivesubproject."""

import hashlib
import io
import os
import tarfile
import tempfile
import zipfile
from unittest.mock import patch

import pytest

from dfetch.manifest.project import ProjectEntry
from dfetch.manifest.version import Version
from dfetch.project.archivesubproject import ArchiveSubProject, _suffix_for_url
from dfetch.vcs.archive import (
    ARCHIVE_EXTENSIONS,
    ArchiveLocalRepo,
    ArchiveRemote,
    is_archive_url,
)

# These are static methods on ArchiveLocalRepo
_check_archive_limits = ArchiveLocalRepo._check_archive_limits
_check_zip_members = ArchiveLocalRepo.check_zip_members
_check_tar_members = ArchiveLocalRepo._check_tar_members


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
# ArchiveLocalRepo.extract - basic smoke test
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


# ---------------------------------------------------------------------------
# Helpers shared by ArchiveSubProject tests
# ---------------------------------------------------------------------------


def _make_tar_gz(path: str, content: bytes = b"hello") -> None:
    """Write a minimal .tar.gz archive containing one file to *path*."""
    with tarfile.open(path, "w:gz") as tf:
        info = tarfile.TarInfo(name="pkg/README.md")
        info.size = len(content)
        tf.addfile(info, io.BytesIO(content))


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _file_url(path: str) -> str:
    return "file:///" + path.lstrip("/")


def _make_subproject(url: str) -> ArchiveSubProject:
    return ArchiveSubProject(
        ProjectEntry({"name": "pkg", "url": url, "vcs": "archive"})
    )


# ---------------------------------------------------------------------------
# ArchiveSubProject._download_and_compute_hash – explicit url parameter
# ---------------------------------------------------------------------------


def test_download_and_compute_hash_default_uses_remote_repo():
    """Without an explicit url the hash is computed from self._remote_repo."""
    with tempfile.TemporaryDirectory() as tmp:
        archive = os.path.join(tmp, "pkg.tar.gz")
        _make_tar_gz(archive)
        url = _file_url(archive)
        sp = _make_subproject(url)

        result = sp._download_and_compute_hash("sha256")

        assert result.algorithm == "sha256"
        assert result.hex_digest == _sha256_file(archive)


def test_download_and_compute_hash_explicit_url_overrides_remote_repo():
    """When *url* is supplied a fresh ArchiveRemote for that URL is used.

    This is the regression guard for the fix: if the manifest URL was changed
    after fetching, freeze must still hash the *original* archive (the one
    recorded in the on-disk revision), not the current manifest URL.
    """
    with tempfile.TemporaryDirectory() as tmp:
        archive_a = os.path.join(tmp, "pkg_a.tar.gz")
        archive_b = os.path.join(tmp, "pkg_b.tar.gz")
        _make_tar_gz(archive_a, content=b"version A")
        _make_tar_gz(archive_b, content=b"version B")
        url_a = _file_url(archive_a)
        url_b = _file_url(archive_b)

        # SubProject points to archive_b (current manifest URL).
        sp = _make_subproject(url_b)

        # Passing url=url_a must use archive_a's content.
        result = sp._download_and_compute_hash("sha256", url=url_a)

        assert result.hex_digest == _sha256_file(archive_a)
        assert result.hex_digest != _sha256_file(archive_b)


# ---------------------------------------------------------------------------
# ArchiveSubProject.freeze_project – uses on-disk revision URL
# ---------------------------------------------------------------------------


def test_freeze_project_uses_on_disk_url_not_manifest_url():
    """freeze_project must hash the archive at the on-disk revision URL.

    Scenario: the manifest URL was updated after the last fetch.  Without the
    fix, freeze would download from the new (current) manifest URL and produce
    a hash that doesn't match the fetched archive.  With the fix it uses the
    URL stored in the on-disk revision.
    """
    with tempfile.TemporaryDirectory() as tmp:
        archive_a = os.path.join(tmp, "pkg_a.tar.gz")
        archive_b = os.path.join(tmp, "pkg_b.tar.gz")
        _make_tar_gz(archive_a, content=b"original fetch")
        _make_tar_gz(archive_b, content=b"updated manifest url")
        url_a = _file_url(archive_a)
        url_b = _file_url(archive_b)

        # SubProject now points to archive_b (manifest was updated after fetch).
        sp = _make_subproject(url_b)

        # Simulate on-disk state: was fetched from url_a (no hash-pin at the time).
        on_disk = Version(revision=url_a)
        with patch.object(sp, "on_disk_version", return_value=on_disk):
            project_entry = ProjectEntry(
                {"name": "pkg", "url": url_b, "vcs": "archive"}
            )
            sp.freeze_project(project_entry)

        expected_hash = f"sha256:{_sha256_file(archive_a)}"
        assert project_entry.hash == expected_hash
        assert _sha256_file(archive_b) not in project_entry.hash
