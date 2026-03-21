"""Unit tests for dfetch.util.util."""

# mypy: ignore-errors
# flake8: noqa

import pytest

from dfetch.util.util import copy_src_subset, hash_directory

# ---------------------------------------------------------------------------
# copy_src_subset – path-traversal protection
# ---------------------------------------------------------------------------


def test_copy_src_subset_copies_file(tmp_path):
    src_root = tmp_path / "src"
    src_root.mkdir()
    (src_root / "lib.h").write_text("content")
    dest = tmp_path / "dest"
    dest.mkdir()

    copy_src_subset(str(src_root), str(dest), "lib.h", keep_licenses=False)

    assert (dest / "lib.h").read_text() == "content"


def test_copy_src_subset_copies_directory(tmp_path):
    src_root = tmp_path / "src"
    src_root.mkdir()
    sub = src_root / "subdir"
    sub.mkdir()
    (sub / "a.c").write_text("code")
    dest = tmp_path / "dest"
    dest.mkdir()

    copy_src_subset(str(src_root), str(dest), "subdir", keep_licenses=False)

    assert (dest / "a.c").read_text() == "code"


@pytest.mark.parametrize(
    "evil_src",
    [
        "../outside.txt",
        "../../etc/passwd",
        "/etc/passwd",
    ],
)
def test_copy_src_subset_rejects_path_traversal(tmp_path, evil_src):
    src_root = tmp_path / "src"
    src_root.mkdir()
    dest = tmp_path / "dest"
    dest.mkdir()

    with pytest.raises(RuntimeError):
        copy_src_subset(str(src_root), str(dest), evil_src, keep_licenses=False)


# ---------------------------------------------------------------------------
# hash_directory – determinism
# ---------------------------------------------------------------------------


def test_hash_directory_is_deterministic(tmp_path):
    """hash_directory must return the same value on repeated calls."""
    d = tmp_path / "proj"
    d.mkdir()
    (d / "a.c").write_text("int main(){}")
    (d / "b.h").write_text("#pragma once")
    sub = d / "src"
    sub.mkdir()
    (sub / "util.c").write_text("void util(){}")

    assert hash_directory(str(d), None) == hash_directory(str(d), None)


def test_hash_directory_differs_when_file_content_changes(tmp_path):
    """Modifying a file must produce a different hash."""
    d = tmp_path / "proj"
    d.mkdir()
    f = d / "file.txt"
    f.write_text("original")

    h1 = hash_directory(str(d), None)
    f.write_text("modified")
    h2 = hash_directory(str(d), None)

    assert h1 != h2


def test_hash_directory_skiplist_excludes_file(tmp_path):
    """Files listed in skiplist must not contribute to the hash."""
    d = tmp_path / "proj"
    d.mkdir()
    (d / "tracked.txt").write_text("data")
    (d / "ignored.txt").write_text("ignored data")

    h_with_skip = hash_directory(str(d), ["ignored.txt"])
    (d / "ignored.txt").write_text("changed ignored data")
    h_with_skip2 = hash_directory(str(d), ["ignored.txt"])

    assert h_with_skip == h_with_skip2
