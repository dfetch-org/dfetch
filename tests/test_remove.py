"""Test the remove command."""

# mypy: ignore-errors
# flake8: noqa

import argparse
from pathlib import Path
from unittest.mock import Mock, patch

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
        fake_manifest.update_dump.assert_called_once()
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
        fake_manifest.update_dump.assert_called_once()
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
        patch("dfetch.commands.remove.safe_rm") as mocked_safe_rm,
        patch("dfetch.commands.remove.shutil.copyfile") as mocked_copyfile,
    ):
        remove(args)

        fake_manifest.remove.assert_not_called()
        fake_manifest.update_dump.assert_not_called()
        mocked_safe_rm.assert_not_called()
        mocked_copyfile.assert_not_called()


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
        fake_manifest.update_dump.assert_not_called()
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
        remove(args)

        # Verify the order of operations through call counts and arguments
        # selected_projects should be called 3 times (once for each project validation)
        assert fake_manifest.selected_projects.call_count == 3
        fake_manifest.selected_projects.assert_any_call(["project1"])
        fake_manifest.selected_projects.assert_any_call(["project2"])
        fake_manifest.selected_projects.assert_any_call(["project3"])

        # remove should be called 2 times (once for each existing project)
        assert fake_manifest.remove.call_count == 2
        fake_manifest.remove.assert_any_call("project1")
        fake_manifest.remove.assert_any_call("project3")

        # update_dump should be called once (after all manifest changes)
        fake_manifest.update_dump.assert_called_once()

        # safe_rm should be called 2 times (once for each existing destination, after persistence)
        assert mocked_safe_rm.call_count == 2
        mocked_safe_rm.assert_any_call(
            "some_dest"
        )  # All destinations are mocked as "some_dest"

        # No backup should be created (VCS superproject)
        mocked_copyfile.assert_not_called()
