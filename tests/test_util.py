"""Unit tests for dfetch.util.util."""

# mypy: ignore-errors
# flake8: noqa

import pytest

from dfetch.util.util import copy_src_subset, hash_directory, prune_files_by_pattern

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


# ---------------------------------------------------------------------------
# prune_files_by_pattern – delete-order safety
# ---------------------------------------------------------------------------


def test_prune_removes_matched_file(tmp_path):
    (tmp_path / "remove_me.txt").write_text("gone")
    prune_files_by_pattern(str(tmp_path), ["remove_me.txt"])
    assert not (tmp_path / "remove_me.txt").exists()


def test_prune_parent_and_child_both_matched_no_error(tmp_path):
    """When a dir and a file inside it both match, removal must not raise.

    Before the fix, removing the parent first left the child path pointing at a
    non-existent location; the subsequent safe_rm call then raised
    FileNotFoundError.
    """
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.c").write_text("int main(){}")

    # "src" matches the directory; "main.c" matches the child inside it.
    prune_files_by_pattern(str(tmp_path), ["src", "main.c"])

    assert not src.exists()


def test_prune_preserves_license_file(tmp_path):
    """License files must survive even when they match a removal pattern."""
    (tmp_path / "LICENSE").write_text("MIT")
    (tmp_path / "delete_me.txt").write_text("gone")

    prune_files_by_pattern(str(tmp_path), ["LICENSE", "delete_me.txt"])

    assert (tmp_path / "LICENSE").exists()
    assert not (tmp_path / "delete_me.txt").exists()


def test_prune_skips_already_removed_paths(tmp_path):
    """Paths that no longer exist after a parent removal are silently skipped."""
    parent = tmp_path / "libs"
    parent.mkdir()
    child = parent / "lib.a"
    child.write_text("binary")
    unrelated = tmp_path / "readme.txt"
    unrelated.write_text("keep")

    # Both "libs" (directory) and "libs/lib.a" (child) match; no exception expected.
    prune_files_by_pattern(str(tmp_path), ["libs", "lib.a"])

    assert not parent.exists()
    assert unrelated.exists()
