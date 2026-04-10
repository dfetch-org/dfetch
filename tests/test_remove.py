"""Test the remove command."""

# mypy: ignore-errors
# flake8: noqa

import argparse
from pathlib import Path
from unittest.mock import Mock, call, patch

import pytest

from dfetch.commands.remove import Remove
from dfetch.project import NoVcsSuperProject
from tests.manifest_mock import mock_manifest


def test_remove_in_vcs_superproject_updates_manifest_in_place() -> None:
    remove = Remove()

    fake_manifest = mock_manifest(
        [{"name": "ext/test-repo-tag"}], path="/tmp/dfetch.yaml"
    )
    fake_superproject = Mock()
    fake_superproject.manifest = fake_manifest
    fake_superproject.root_directory = Path("/tmp")

    args = argparse.Namespace(projects=["ext/test-repo-tag"])

    with (
        patch(
            "dfetch.commands.remove.create_super_project",
            return_value=fake_superproject,
        ),
        patch("dfetch.commands.remove.in_directory"),
        patch("dfetch.commands.remove.safe_rm") as mocked_safe_rm,
        patch("dfetch.commands.remove.shutil.copyfile") as mocked_copyfile,
    ):
        remove(args)

        fake_manifest.remove.assert_called_once_with("ext/test-repo-tag")
        fake_manifest.dump.assert_called_once()
        mocked_safe_rm.assert_called_once_with("some_dest")
        mocked_copyfile.assert_not_called()


def test_remove_outside_vcs_creates_manifest_backup() -> None:
    remove = Remove()

    fake_manifest = mock_manifest(
        [{"name": "ext/test-repo-tag"}], path="/tmp/dfetch.yaml"
    )
    fake_superproject = NoVcsSuperProject(fake_manifest, Path("/tmp"))

    args = argparse.Namespace(projects=["ext/test-repo-tag"])

    with (
        patch(
            "dfetch.commands.remove.create_super_project",
            return_value=fake_superproject,
        ),
        patch("dfetch.commands.remove.in_directory"),
        patch("dfetch.commands.remove.safe_rm") as mocked_safe_rm,
        patch("dfetch.commands.remove.shutil.copyfile") as mocked_copyfile,
    ):
        remove(args)

        fake_manifest.remove.assert_called_once_with("ext/test-repo-tag")
        fake_manifest.dump.assert_called_once()
        mocked_safe_rm.assert_called_once_with("some_dest")
        mocked_copyfile.assert_called_once_with(
            "/tmp/dfetch.yaml", "/tmp/dfetch.yaml.backup"
        )


def test_remove_nonexistent_project_logs_error() -> None:
    """Remove command should log an error when trying to remove a nonexistent project."""
    remove = Remove()

    fake_manifest = mock_manifest(
        [{"name": "ext/test-repo-tag"}], path="/tmp/dfetch.yaml"
    )
    fake_superproject = Mock()
    fake_superproject.manifest = fake_manifest
    fake_superproject.root_directory = Path("/tmp")

    args = argparse.Namespace(projects=["nonexistent"])

    with (
        patch(
            "dfetch.commands.remove.create_super_project",
            return_value=fake_superproject,
        ),
        patch("dfetch.commands.remove.in_directory"),
        patch("dfetch.commands.remove.logger.print_info_line") as mocked_print_info,
        patch("dfetch.commands.remove.safe_rm") as mocked_safe_rm,
        patch("dfetch.commands.remove.shutil.copyfile") as mocked_copyfile,
    ):
        remove(args)

        fake_manifest.remove.assert_not_called()
        fake_manifest.dump.assert_not_called()
        mocked_safe_rm.assert_not_called()
        mocked_copyfile.assert_not_called()
        mocked_print_info.assert_called_once_with(
            "nonexistent", "project 'nonexistent' not found in manifest"
        )


def test_remove_with_empty_projects_list_does_nothing() -> None:
    """Remove command should do nothing when no projects are specified."""
    remove = Remove()

    fake_manifest = mock_manifest(
        [{"name": "ext/test-repo-tag"}], path="/tmp/dfetch.yaml"
    )
    fake_superproject = Mock()
    fake_superproject.manifest = fake_manifest
    fake_superproject.root_directory = Path("/tmp")

    args = argparse.Namespace(projects=[])

    with (
        patch(
            "dfetch.commands.remove.create_super_project",
            return_value=fake_superproject,
        ),
        patch("dfetch.commands.remove.in_directory"),
        patch("dfetch.commands.remove.safe_rm") as mocked_safe_rm,
        patch("dfetch.commands.remove.shutil.copyfile") as mocked_copyfile,
    ):
        remove(args)

        fake_manifest.remove.assert_not_called()
        fake_manifest.dump.assert_not_called()
        mocked_safe_rm.assert_not_called()
        mocked_copyfile.assert_not_called()


def test_remove_multiple_projects_atomically() -> None:
    """Remove command should perform operations atomically: validate all, then update manifest, then persist, then delete files."""
    remove = Remove()

    fake_manifest = mock_manifest(
        [{"name": "project1", "dst": "dest1"}, {"name": "project3", "dst": "dest3"}],
        path="/tmp/dfetch.yaml",
    )
    fake_superproject = Mock()
    fake_superproject.manifest = fake_manifest
    fake_superproject.root_directory = Path("/tmp")

    args = argparse.Namespace(projects=["project1", "project2", "project3"])

    with (
        patch(
            "dfetch.commands.remove.create_super_project",
            return_value=fake_superproject,
        ),
        patch("dfetch.commands.remove.in_directory"),
        patch("dfetch.commands.remove.safe_rm") as mocked_safe_rm,
        patch("dfetch.commands.remove.shutil.copyfile") as mocked_copyfile,
    ):

        def _dump_side_effect():
            # Ensure no filesystem deletion happened before persistence
            mocked_safe_rm.assert_not_called()

        fake_manifest.dump.side_effect = _dump_side_effect

        remove(args)

        # Verify exact call order: validate all, then remove found projects, then dump, then delete
        fake_manifest.assert_has_calls(
            [
                call.selected_projects(["project1"]),
                call.selected_projects(["project2"]),
                call.selected_projects(["project3"]),
                call.remove("project1"),
                call.remove("project3"),
                call.dump(),
            ],
            any_order=False,
        )

        # safe_rm called once per existing project destination, after dump
        assert mocked_safe_rm.call_count == 2
        mocked_safe_rm.assert_has_calls(
            [call("some_dest"), call("some_dest")],
            any_order=False,
        )

        # No backup should be created (VCS superproject)
        mocked_copyfile.assert_not_called()
