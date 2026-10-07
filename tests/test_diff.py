"""Test the diff command."""

# mypy: ignore-errors
# flake8: noqa

import argparse
from unittest.mock import Mock, patch

import pytest

from dfetch.commands.diff import Diff
from tests.manifest_mock import mock_manifest


def _run_diff(tmp_path, name):
    root = tmp_path / "superproject"
    root.mkdir()
    (root / "some_dest").mkdir()

    fake_superproject = Mock()
    fake_superproject.manifest = mock_manifest([{"name": name}])
    fake_superproject.root_directory = str(root)
    fake_superproject.diff.return_value = "some patch content"

    args = argparse.Namespace(projects=[name], revs="HEAD")

    with patch(
        "dfetch.commands.diff.create_super_project", return_value=fake_superproject
    ):
        Diff()(args)

    return root


def test_diff_writes_patch_in_superproject_root(tmp_path):
    root = _run_diff(tmp_path, "my_project")

    assert (root / "my_project.patch").read_text(encoding="UTF-8") == (
        "some patch content"
    )


@pytest.mark.parametrize(
    "name",
    [
        "../pwn",
        "../../pwn",
        "sub/../../pwn",
    ],
)
def test_diff_refuses_patch_path_outside_superproject(tmp_path, name):
    target = (tmp_path / "superproject" / f"{name}.patch").resolve()

    with pytest.raises(RuntimeError):
        _run_diff(tmp_path, name)

    assert not target.exists()


def test_diff_refuses_absolute_patch_path(tmp_path):
    target = tmp_path / "outside" / "pwn"
    target.parent.mkdir()

    with pytest.raises(RuntimeError):
        _run_diff(tmp_path, str(target))

    assert not (target.parent / "pwn.patch").exists()


def test_diff_refuses_patch_symlink_outside_superproject(tmp_path):
    outside = tmp_path / "outside.patch"
    outside.write_text("original", encoding="UTF-8")
    root = tmp_path / "superproject"
    root.mkdir()
    (root / "my_project.patch").symlink_to(outside)

    fake_superproject = Mock()
    fake_superproject.manifest = mock_manifest([{"name": "my_project"}])
    fake_superproject.root_directory = str(root)
    fake_superproject.diff.return_value = "some patch content"
    (root / "some_dest").mkdir()

    with patch(
        "dfetch.commands.diff.create_super_project", return_value=fake_superproject
    ):
        with pytest.raises(RuntimeError):
            Diff()(argparse.Namespace(projects=["my_project"], revs="HEAD"))

    assert outside.read_text(encoding="UTF-8") == "original"
