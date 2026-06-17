"""Tests for dfetch/commands/freeze.py."""

# mypy: ignore-errors
# flake8: noqa

import argparse
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from dfetch.commands.freeze import Freeze
from dfetch.project.superproject import NoVcsSuperProject
from tests.manifest_mock import mock_manifest


def _make_args(projects=None):
    """Build a minimal Namespace for Freeze.__call__."""
    args = argparse.Namespace()
    args.projects = projects or []
    return args


def _make_superproject(manifest, is_novcs=False, root=Path("/tmp")):
    """Return a mock superproject."""
    if is_novcs:
        superproject = Mock(spec=NoVcsSuperProject)
    else:
        superproject = Mock()
    superproject.manifest = manifest
    superproject.root_directory = root
    return superproject


def test_freeze_no_projects():
    """When there are no projects, manifest.dump is not called."""
    freeze = Freeze()
    manifest = mock_manifest([])
    superproject = _make_superproject(manifest)

    with patch(
        "dfetch.commands.freeze.create_super_project", return_value=superproject
    ):
        with patch("dfetch.commands.freeze.in_directory"):
            freeze(_make_args())

    manifest.dump.assert_not_called()


def test_freeze_project_returns_version_dumps_manifest():
    """When freeze_project returns a version string, manifest.dump is called."""
    freeze = Freeze()
    manifest = mock_manifest([{"name": "mymod"}])
    superproject = _make_superproject(manifest)

    with patch(
        "dfetch.commands.freeze.create_super_project", return_value=superproject
    ):
        with patch("dfetch.commands.freeze.in_directory"):
            with patch(
                "dfetch.commands.freeze.dfetch.project.create_sub_project"
            ) as mock_create:
                mock_sub = Mock()
                mock_sub.freeze_project.return_value = "v1.0"
                mock_sub.on_disk_version.return_value = "v1.0"
                mock_create.return_value = mock_sub

                freeze(_make_args())

    manifest.dump.assert_called_once()


def test_freeze_project_already_pinned_logs_info():
    """When freeze_project returns None and on_disk_version is set, info is logged."""
    freeze = Freeze()
    manifest = mock_manifest([{"name": "pinned_mod"}])
    superproject = _make_superproject(manifest)

    with patch(
        "dfetch.commands.freeze.create_super_project", return_value=superproject
    ):
        with patch("dfetch.commands.freeze.in_directory"):
            with patch(
                "dfetch.commands.freeze.dfetch.project.create_sub_project"
            ) as mock_create:
                with patch("dfetch.commands.freeze.logger") as mock_logger:
                    mock_sub = Mock()
                    mock_sub.freeze_project.return_value = None
                    mock_sub.on_disk_version.return_value = "v1.0"
                    mock_create.return_value = mock_sub

                    freeze(_make_args())

                    mock_logger.print_info_line.assert_called_once()
                    call_args = mock_logger.print_info_line.call_args[0]
                    assert "Already pinned" in call_args[1]


def test_freeze_project_no_version_on_disk_logs_warning():
    """When freeze_project returns None and on_disk_version is falsy, a warning is logged."""
    freeze = Freeze()
    manifest = mock_manifest([{"name": "unfetched_mod"}])
    superproject = _make_superproject(manifest)

    with patch(
        "dfetch.commands.freeze.create_super_project", return_value=superproject
    ):
        with patch("dfetch.commands.freeze.in_directory"):
            with patch(
                "dfetch.commands.freeze.dfetch.project.create_sub_project"
            ) as mock_create:
                with patch("dfetch.commands.freeze.logger") as mock_logger:
                    mock_sub = Mock()
                    mock_sub.freeze_project.return_value = None
                    mock_sub.on_disk_version.return_value = None
                    mock_create.return_value = mock_sub

                    freeze(_make_args())

                    mock_logger.print_warning_line.assert_called_once()
                    call_args = mock_logger.print_warning_line.call_args[0]
                    assert "No version on disk" in call_args[1]


def test_freeze_runtime_error_raises_at_end():
    """When freeze_project raises RuntimeError, the command raises RuntimeError after the loop."""
    freeze = Freeze()
    manifest = mock_manifest([{"name": "bad_mod"}])
    superproject = _make_superproject(manifest)

    with patch(
        "dfetch.commands.freeze.create_super_project", return_value=superproject
    ):
        with patch("dfetch.commands.freeze.in_directory"):
            with patch(
                "dfetch.commands.freeze.dfetch.project.create_sub_project"
            ) as mock_create:
                mock_sub = Mock()
                mock_sub.freeze_project.side_effect = RuntimeError("fetch failed")
                mock_create.return_value = mock_sub

                with pytest.raises(RuntimeError):
                    freeze(_make_args())


def test_freeze_novcs_creates_backup():
    """When the superproject is NoVcsSuperProject, a .backup copy of the manifest is created."""
    freeze = Freeze()
    manifest = mock_manifest([], path="/some/dfetch.yaml")
    superproject = _make_superproject(manifest, is_novcs=True)

    with patch(
        "dfetch.commands.freeze.create_super_project", return_value=superproject
    ):
        with patch("dfetch.commands.freeze.in_directory"):
            with patch("dfetch.commands.freeze.shutil.copyfile") as mock_copy:
                freeze(_make_args())

                mock_copy.assert_called_once_with(
                    "/some/dfetch.yaml", "/some/dfetch.yaml.backup"
                )


def test_freeze_vcs_no_backup():
    """When the superproject has VCS, no .backup copy of the manifest is created."""
    freeze = Freeze()
    manifest = mock_manifest([], path="/some/dfetch.yaml")
    # Deliberately NOT a NoVcsSuperProject
    superproject = Mock()
    superproject.manifest = manifest
    superproject.root_directory = Path("/tmp")

    with patch(
        "dfetch.commands.freeze.create_super_project", return_value=superproject
    ):
        with patch("dfetch.commands.freeze.in_directory"):
            with patch("dfetch.commands.freeze.shutil.copyfile") as mock_copy:
                freeze(_make_args())

                mock_copy.assert_not_called()
