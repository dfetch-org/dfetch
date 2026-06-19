"""Test the review-patch command."""

# mypy: ignore-errors
# flake8: noqa

import argparse
from pathlib import Path
from unittest.mock import ANY, Mock, call, patch

import pytest

from dfetch.commands.review_patch import ReviewPatch
from dfetch.project.gitsuperproject import GitSuperProject
from dfetch.project.superproject import NoVcsSuperProject
from tests.manifest_mock import mock_manifest

_PATCH_FILES = ["patches/first.patch", "patches/second.patch"]


def _make_args(projects=None, count=None, interactive=False):
    args = argparse.Namespace(
        projects=projects or [],
        count=count,
        interactive=interactive,
    )
    return args


def _make_superproject(is_git=True, has_local_changes=False):
    sp = Mock(spec=GitSuperProject) if is_git else Mock()
    sp.manifest = mock_manifest([{"name": "my_project"}])
    sp.root_directory = Path("/tmp")
    sp.ignored_files.return_value = []
    sp.eol_preferences = Mock(return_value={})
    sp.has_local_changes_in_dir.return_value = has_local_changes
    return sp


def _make_subproject(patches=None, on_disk_version: str | None = "v1"):
    sub = Mock()
    sub.patch = patches if patches is not None else _PATCH_FILES
    sub.local_path = "my_project"
    sub.on_disk_version.return_value = on_disk_version
    return sub


# ---------------------------------------------------------------------------
# Git happy path
# ---------------------------------------------------------------------------


def test_review_all_patches_calls_update_add_path_update():
    cmd = ReviewPatch()
    fake_super = _make_superproject(is_git=True)
    fake_sub = _make_subproject()

    with patch(
        "dfetch.commands.review_patch.create_super_project", return_value=fake_super
    ):
        with patch("dfetch.commands.command.in_directory"):
            with patch(
                "dfetch.commands.review_patch.create_sub_project", return_value=fake_sub
            ):
                with patch("dfetch.commands.review_patch.is_tty", return_value=False):
                    cmd(_make_args())

    fake_sub.update.assert_called_once_with(
        force=True,
        ignored_files_callback=ANY,
        patch_count=0,
        eol_preferences_callback=ANY,
    )
    fake_super.add_path.assert_called_once_with("my_project")
    fake_sub.apply_patches.assert_called_once_with(-1)
    fake_super.restore_worktree.assert_not_called()
    fake_super.restore_staged.assert_called_once_with("my_project")


def test_review_count_1_uses_patch_count_1():
    cmd = ReviewPatch()
    fake_super = _make_superproject(is_git=True)
    fake_sub = _make_subproject()

    with patch(
        "dfetch.commands.review_patch.create_super_project", return_value=fake_super
    ):
        with patch("dfetch.commands.command.in_directory"):
            with patch(
                "dfetch.commands.review_patch.create_sub_project", return_value=fake_sub
            ):
                with patch("dfetch.commands.review_patch.is_tty", return_value=False):
                    cmd(_make_args(count=1))

    fake_sub.update.assert_called_once_with(
        force=True,
        ignored_files_callback=ANY,
        patch_count=0,
        eol_preferences_callback=ANY,
    )
    apply_calls = fake_sub.apply_patches.call_args_list
    assert apply_calls[0] == call(1), "first apply must apply exactly 1 patch"
    assert (
        apply_calls[1] == call()
    ), "finally must restore all patches via apply_patches()"
    fake_super.restore_worktree.assert_called_once_with("my_project")


# ---------------------------------------------------------------------------
# SVN path (no add_path / restore_staged)
# ---------------------------------------------------------------------------


def test_svn_superproject_warns_and_skips_staging():
    cmd = ReviewPatch()
    fake_super = _make_superproject(is_git=False)  # not GitSuperProject
    fake_sub = _make_subproject()

    with patch(
        "dfetch.commands.review_patch.create_super_project", return_value=fake_super
    ):
        with patch("dfetch.commands.command.in_directory"):
            with patch(
                "dfetch.commands.review_patch.create_sub_project", return_value=fake_sub
            ):
                with patch("dfetch.commands.review_patch.is_tty", return_value=False):
                    with patch("dfetch.commands.review_patch.logger") as mock_log:
                        cmd(_make_args())

    mock_log.warning.assert_called_once()
    fake_super.add_path.assert_not_called()
    fake_super.restore_staged.assert_not_called()
    fake_sub.update.assert_called_once_with(
        force=True,
        ignored_files_callback=ANY,
        patch_count=0,
        eol_preferences_callback=ANY,
    )
    fake_sub.apply_patches.assert_called_once_with(-1)


# ---------------------------------------------------------------------------
# Skip scenarios
# ---------------------------------------------------------------------------


def test_no_patches_logs_warning_and_skips():
    cmd = ReviewPatch()
    fake_super = _make_superproject(is_git=True)
    fake_sub = _make_subproject(patches=[])

    with patch(
        "dfetch.commands.review_patch.create_super_project", return_value=fake_super
    ):
        with patch("dfetch.commands.command.in_directory"):
            with patch(
                "dfetch.commands.review_patch.create_sub_project", return_value=fake_sub
            ):
                cmd(_make_args())

    fake_sub.update.assert_not_called()
    fake_super.add_path.assert_not_called()


def test_never_fetched_logs_warning_and_skips():
    cmd = ReviewPatch()
    fake_super = _make_superproject(is_git=True)
    fake_sub = _make_subproject(on_disk_version=None)

    with patch(
        "dfetch.commands.review_patch.create_super_project", return_value=fake_super
    ):
        with patch("dfetch.commands.command.in_directory"):
            with patch(
                "dfetch.commands.review_patch.create_sub_project", return_value=fake_sub
            ):
                cmd(_make_args())

    fake_sub.update.assert_not_called()
    fake_super.add_path.assert_not_called()


def test_local_changes_logs_warning_and_skips():
    cmd = ReviewPatch()
    fake_super = _make_superproject(is_git=True, has_local_changes=True)
    fake_sub = _make_subproject()

    with patch(
        "dfetch.commands.review_patch.create_super_project", return_value=fake_super
    ):
        with patch("dfetch.commands.command.in_directory"):
            with patch(
                "dfetch.commands.review_patch.create_sub_project", return_value=fake_sub
            ):
                cmd(_make_args())

    fake_sub.update.assert_not_called()
    fake_super.add_path.assert_not_called()


# ---------------------------------------------------------------------------
# Error scenarios
# ---------------------------------------------------------------------------


def test_no_vcs_superproject_raises():
    cmd = ReviewPatch()
    fake_super = Mock(spec=NoVcsSuperProject)

    with patch(
        "dfetch.commands.review_patch.create_super_project", return_value=fake_super
    ):
        with pytest.raises(RuntimeError):
            cmd(_make_args())


def test_interactive_without_tty_raises():
    cmd = ReviewPatch()
    fake_super = _make_superproject(is_git=True)

    with patch(
        "dfetch.commands.review_patch.create_super_project", return_value=fake_super
    ):
        with patch("dfetch.commands.review_patch.is_tty", return_value=False):
            with pytest.raises(RuntimeError, match="interactive"):
                cmd(_make_args(interactive=True))


def test_negative_count_raises():
    cmd = ReviewPatch()
    fake_super = _make_superproject(is_git=True)

    with patch(
        "dfetch.commands.review_patch.create_super_project", return_value=fake_super
    ):
        with pytest.raises(RuntimeError, match="--count must be >= 0"):
            cmd(_make_args(count=-1))
