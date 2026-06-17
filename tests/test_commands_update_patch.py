"""Tests for dfetch.commands.update_patch.UpdatePatch."""

# mypy: ignore-errors
# flake8: noqa

import argparse
import pathlib
from unittest.mock import MagicMock, Mock, patch

import pytest

from dfetch.commands.update_patch import UpdatePatch
from dfetch.manifest.project import ProjectEntry
from dfetch.project.superproject import NoVcsSuperProject
from tests.manifest_mock import mock_manifest


def _default_args(projects=None):
    args = argparse.Namespace()
    args.projects = projects or []
    return args


def _make_git_superproject(root="/repo", projects=None):
    """Return a mock that passes isinstance(sp, GitSuperProject)."""
    from dfetch.project.gitsuperproject import GitSuperProject

    fake_sp = MagicMock(spec=GitSuperProject)
    fake_sp.root_directory = pathlib.Path(root)
    fake_sp.manifest = mock_manifest(projects or [])
    return fake_sp


def _make_svn_superproject(root="/repo", projects=None):
    """Return a non-Git, non-NoVcs mock superproject."""
    from dfetch.project.svnsuperproject import SvnSuperProject

    fake_sp = MagicMock(spec=SvnSuperProject)
    fake_sp.root_directory = pathlib.Path(root)
    fake_sp.manifest = mock_manifest(projects or [])
    return fake_sp


def _make_novcs_superproject():
    fake_sp = MagicMock(spec=NoVcsSuperProject)
    fake_sp.root_directory = pathlib.Path("/repo")
    fake_sp.manifest = mock_manifest([])
    return fake_sp


# ---------------------------------------------------------------------------
# __call__: high-level routing
# ---------------------------------------------------------------------------


def test_raises_for_novcs_superproject():
    """update-patch raises RuntimeError when superproject has no VCS."""
    cmd = UpdatePatch()
    fake_sp = _make_novcs_superproject()

    with patch("dfetch.commands.update_patch.create_super_project", return_value=fake_sp):
        with patch("dfetch.commands.update_patch.in_directory"):
            with pytest.raises(RuntimeError, match="not under version control"):
                cmd(_default_args())


def test_warns_when_not_git_superproject():
    """update-patch logs a warning when the superproject is SVN (not Git)."""
    cmd = UpdatePatch()
    fake_sp = _make_svn_superproject(projects=[])

    with patch("dfetch.commands.update_patch.create_super_project", return_value=fake_sp):
        with patch("dfetch.commands.update_patch.in_directory") as mock_indir:
            mock_indir.return_value.__enter__ = Mock(return_value=None)
            mock_indir.return_value.__exit__ = Mock(return_value=False)
            with patch("dfetch.commands.update_patch.logger") as mock_logger:
                cmd(_default_args())
                mock_logger.warning.assert_called_once()


def test_error_during_process_raises_at_end():
    """A RuntimeError in _process_project sets had_errors; RuntimeError raised after loop."""
    cmd = UpdatePatch()
    fake_sp = _make_git_superproject(projects=[{"name": "mylib"}])

    with patch("dfetch.commands.update_patch.create_super_project", return_value=fake_sp):
        with patch("dfetch.commands.update_patch.in_directory") as mock_indir:
            mock_indir.return_value.__enter__ = Mock(return_value=None)
            mock_indir.return_value.__exit__ = Mock(return_value=False)
            with patch.object(
                cmd, "_process_project", side_effect=RuntimeError("boom")
            ):
                with pytest.raises(RuntimeError):
                    cmd(_default_args())


def test_no_projects_runs_without_error():
    """update-patch with no projects in manifest completes without error."""
    cmd = UpdatePatch()
    fake_sp = _make_git_superproject(projects=[])

    with patch("dfetch.commands.update_patch.create_super_project", return_value=fake_sp):
        with patch("dfetch.commands.update_patch.in_directory") as mock_indir:
            mock_indir.return_value.__enter__ = Mock(return_value=None)
            mock_indir.return_value.__exit__ = Mock(return_value=False)
            cmd(_default_args())  # must not raise


# ---------------------------------------------------------------------------
# _process_project
# ---------------------------------------------------------------------------


def _make_project_entry(name="mylib", patch_files=None):
    project = Mock(spec=ProjectEntry)
    project.name = name
    project.destination = f"libs/{name}"
    return project


def test_process_project_skips_when_no_patch():
    """_process_project logs a warning and returns early when subproject has no patch."""
    cmd = UpdatePatch()
    superproject = _make_git_superproject()
    project = _make_project_entry()

    mock_subproject = Mock()
    mock_subproject.patch = []
    mock_subproject.local_path = "libs/mylib"

    with patch("dfetch.project.create_sub_project", return_value=mock_subproject):
        with patch("dfetch.commands.update_patch.logger") as mock_logger:
            cmd._process_project(superproject, project)
            mock_logger.print_warning_line.assert_called_once()


def test_process_project_skips_when_not_fetched():
    """_process_project logs a warning and returns when on_disk_version is None."""
    cmd = UpdatePatch()
    superproject = _make_git_superproject()
    project = _make_project_entry()

    mock_subproject = Mock()
    mock_subproject.patch = ["some.patch"]
    mock_subproject.on_disk_version.return_value = None
    mock_subproject.local_path = "libs/mylib"

    with patch("dfetch.project.create_sub_project", return_value=mock_subproject):
        with patch("dfetch.commands.update_patch.logger") as mock_logger:
            cmd._process_project(superproject, project)
            mock_logger.print_warning_line.assert_called_once()


def test_process_project_skips_when_uncommitted_changes():
    """_process_project logs a warning when the project dir has uncommitted changes."""
    cmd = UpdatePatch()
    superproject = _make_git_superproject()
    superproject.has_local_changes_in_dir.return_value = True
    project = _make_project_entry()

    mock_subproject = Mock()
    mock_subproject.patch = ["some.patch"]
    mock_subproject.on_disk_version.return_value = Mock()
    mock_subproject.local_path = "libs/mylib"

    with patch("dfetch.project.create_sub_project", return_value=mock_subproject):
        with patch("dfetch.commands.update_patch.logger") as mock_logger:
            cmd._process_project(superproject, project)
            mock_logger.print_warning_line.assert_called_once()


# ---------------------------------------------------------------------------
# _update_patch
# ---------------------------------------------------------------------------


def test_update_patch_writes_patch_text_when_nonempty(tmp_path):
    """_update_patch writes patch_text to the patch file."""
    cmd = UpdatePatch()
    patch_file = tmp_path / "my.patch"
    patch_file.write_text("old content", encoding="utf-8")

    with patch("dfetch.commands.update_patch.check_no_path_traversal"):
        result = cmd._update_patch(str(patch_file), tmp_path, "mylib", "new diff")

    assert result is not None
    assert patch_file.read_text(encoding="utf-8") == "new diff"


def test_update_patch_logs_info_when_no_diff(tmp_path):
    """_update_patch logs 'No diffs found' and does not overwrite patch when text is empty."""
    cmd = UpdatePatch()
    patch_file = tmp_path / "my.patch"
    patch_file.write_text("old content", encoding="utf-8")

    with patch("dfetch.commands.update_patch.check_no_path_traversal"):
        with patch("dfetch.commands.update_patch.logger") as mock_logger:
            result = cmd._update_patch(str(patch_file), tmp_path, "mylib", "")
            mock_logger.print_info_line.assert_called_once()

    assert result is not None
    assert patch_file.read_text(encoding="utf-8") == "old content"


def test_update_patch_returns_none_when_path_traversal(tmp_path):
    """_update_patch returns None when patch file is outside root."""
    cmd = UpdatePatch()

    with patch(
        "dfetch.commands.update_patch.check_no_path_traversal",
        side_effect=RuntimeError("traversal"),
    ):
        with patch("dfetch.commands.update_patch.logger") as mock_logger:
            result = cmd._update_patch("/etc/evil.patch", tmp_path, "mylib", "diff")
            mock_logger.print_warning_line.assert_called_once()

    assert result is None
