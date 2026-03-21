"""Unit tests for dfetch.util.util."""

# mypy: ignore-errors
# flake8: noqa

import pytest

from dfetch.util.util import copy_src_subset

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
