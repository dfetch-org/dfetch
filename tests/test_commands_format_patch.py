"""Tests for dfetch.commands.format_patch."""

# mypy: ignore-errors
# flake8: noqa

import argparse
import pathlib
from unittest.mock import MagicMock, Mock, patch

import pytest

from dfetch.commands.format_patch import FormatPatch, _determine_target_patch_type
from dfetch.project.gitsubproject import GitSubProject
from dfetch.project.svnsubproject import SvnSubProject
from dfetch.vcs.patch import PatchType
from tests.manifest_mock import mock_manifest

# ---------------------------------------------------------------------------
# _determine_target_patch_type
# ---------------------------------------------------------------------------


def test_determine_patch_type_git():
    """Git subprojects use PatchType.GIT."""
    with patch("dfetch.project.gitsubproject.GitRemote"):
        from dfetch.manifest.project import ProjectEntry

        sp = MagicMock(spec=GitSubProject)
        assert _determine_target_patch_type(sp) is PatchType.GIT


def test_determine_patch_type_svn():
    """SVN subprojects use PatchType.SVN."""
    sp = MagicMock(spec=SvnSubProject)
    assert _determine_target_patch_type(sp) is PatchType.SVN


def test_determine_patch_type_other():
    """Other subprojects (archive etc.) use PatchType.PLAIN."""
    from dfetch.project.archivesubproject import ArchiveSubProject

    sp = MagicMock(spec=ArchiveSubProject)
    assert _determine_target_patch_type(sp) is PatchType.PLAIN


# ---------------------------------------------------------------------------
# FormatPatch.__call__: routing and error handling
# ---------------------------------------------------------------------------


def _default_args(projects=None, output_dir="."):
    args = argparse.Namespace()
    args.projects = projects or []
    args.output_directory = output_dir
    return args


def _make_superproject(root="/repo", projects=None):
    from dfetch.project.gitsuperproject import GitSuperProject

    fake_sp = MagicMock(spec=GitSuperProject)
    fake_sp.root_directory = pathlib.Path(root)
    fake_sp.manifest = mock_manifest(projects or [])
    fake_sp.get_username.return_value = "alice"
    fake_sp.get_useremail.return_value = "alice@example.com"
    return fake_sp


def test_format_patch_no_projects_runs_without_error(tmp_path):
    """format-patch with no projects in manifest completes without error."""
    cmd = FormatPatch()
    fake_sp = _make_superproject(root=str(tmp_path), projects=[])

    with patch(
        "dfetch.commands.format_patch.create_super_project", return_value=fake_sp
    ):
        with patch("dfetch.commands.format_patch.in_directory") as mock_indir:
            mock_indir.return_value.__enter__ = Mock(return_value=None)
            mock_indir.return_value.__exit__ = Mock(return_value=False)
            with patch("dfetch.commands.format_patch.check_no_path_traversal"):
                cmd(_default_args(output_dir=str(tmp_path)))


def test_format_patch_warns_when_no_patch_file(tmp_path):
    """format-patch logs a warning and continues when subproject has no patch."""
    cmd = FormatPatch()
    fake_sp = _make_superproject(root=str(tmp_path), projects=[{"name": "mylib"}])

    mock_subproject = Mock()
    mock_subproject.patch = []

    with patch(
        "dfetch.commands.format_patch.create_super_project", return_value=fake_sp
    ):
        with patch("dfetch.commands.format_patch.in_directory") as mock_indir:
            mock_indir.return_value.__enter__ = Mock(return_value=None)
            mock_indir.return_value.__exit__ = Mock(return_value=False)
            with patch("dfetch.commands.format_patch.check_no_path_traversal"):
                with patch(
                    "dfetch.project.create_sub_project", return_value=mock_subproject
                ):
                    with patch("dfetch.commands.format_patch.logger") as mock_logger:
                        cmd(_default_args(output_dir=str(tmp_path)))
                        mock_logger.print_warning_line.assert_called_once()


def test_format_patch_runtime_error_raises_at_end(tmp_path):
    """RuntimeError in the loop sets had_errors; command raises RuntimeError after loop."""
    cmd = FormatPatch()
    fake_sp = _make_superproject(root=str(tmp_path), projects=[{"name": "mylib"}])

    mock_subproject = Mock()
    mock_subproject.patch = ["some.patch"]
    mock_subproject.on_disk_version.side_effect = RuntimeError("boom")

    with patch(
        "dfetch.commands.format_patch.create_super_project", return_value=fake_sp
    ):
        with patch("dfetch.commands.format_patch.in_directory") as mock_indir:
            mock_indir.return_value.__enter__ = Mock(return_value=None)
            mock_indir.return_value.__exit__ = Mock(return_value=False)
            with patch("dfetch.commands.format_patch.check_no_path_traversal"):
                with patch(
                    "dfetch.project.create_sub_project", return_value=mock_subproject
                ):
                    with pytest.raises(RuntimeError):
                        cmd(_default_args(output_dir=str(tmp_path)))
