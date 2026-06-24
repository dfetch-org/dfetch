"""Test the replay-patches command."""

# mypy: ignore-errors
# flake8: noqa

import argparse
import tempfile
from pathlib import Path
from unittest.mock import ANY, Mock, call, patch

import pytest

from dfetch.commands.replay_patches import ReplayPatches
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
    with tempfile.NamedTemporaryFile(delete=False, suffix=".yaml", mode="wb") as f:
        f.write(b"dfetch:\n  patch: patches/first.patch\n")
        sub.metadata_path = f.name
    return sub


# ---------------------------------------------------------------------------
# Git happy path
# ---------------------------------------------------------------------------


def test_review_all_patches_calls_update_add_path_update():
    cmd = ReplayPatches()
    fake_super = _make_superproject(is_git=True)
    fake_sub = _make_subproject()

    with patch(
        "dfetch.commands.replay_patches.create_super_project", return_value=fake_super
    ):
        with patch("dfetch.commands.command.in_directory"):
            with patch(
                "dfetch.commands.replay_patches.create_sub_project",
                return_value=fake_sub,
            ):
                with patch("dfetch.commands.replay_patches.is_tty", return_value=False):
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
    cmd = ReplayPatches()
    fake_super = _make_superproject(is_git=True)
    fake_sub = _make_subproject()

    with patch(
        "dfetch.commands.replay_patches.create_super_project", return_value=fake_super
    ):
        with patch("dfetch.commands.command.in_directory"):
            with patch(
                "dfetch.commands.replay_patches.create_sub_project",
                return_value=fake_sub,
            ):
                with patch("dfetch.commands.replay_patches.is_tty", return_value=False):
                    cmd(_make_args(count=1))

    fake_sub.update.assert_called_once_with(
        force=True,
        ignored_files_callback=ANY,
        patch_count=0,
        eol_preferences_callback=ANY,
    )
    fake_sub.apply_patches.assert_called_once_with(1)
    fake_super.restore_from_head.assert_called_once_with("my_project")
    fake_super.restore_worktree.assert_not_called()
    fake_super.restore_staged.assert_not_called()


# ---------------------------------------------------------------------------
# SVN path (no add_path / restore_staged)
# ---------------------------------------------------------------------------


def test_svn_superproject_warns_and_skips_staging():
    cmd = ReplayPatches()
    fake_super = _make_superproject(is_git=False)  # not GitSuperProject
    fake_sub = _make_subproject()

    with patch(
        "dfetch.commands.replay_patches.create_super_project", return_value=fake_super
    ):
        with patch("dfetch.commands.command.in_directory"):
            with patch(
                "dfetch.commands.replay_patches.create_sub_project",
                return_value=fake_sub,
            ):
                with patch("dfetch.commands.replay_patches.is_tty", return_value=False):
                    with patch("dfetch.commands.replay_patches.logger") as mock_log:
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
    cmd = ReplayPatches()
    fake_super = _make_superproject(is_git=True)
    fake_sub = _make_subproject(patches=[])

    with patch(
        "dfetch.commands.replay_patches.create_super_project", return_value=fake_super
    ):
        with patch("dfetch.commands.command.in_directory"):
            with patch(
                "dfetch.commands.replay_patches.create_sub_project",
                return_value=fake_sub,
            ):
                cmd(_make_args())

    fake_sub.update.assert_not_called()
    fake_super.add_path.assert_not_called()


def test_never_fetched_logs_warning_and_skips():
    cmd = ReplayPatches()
    fake_super = _make_superproject(is_git=True)
    fake_sub = _make_subproject(on_disk_version=None)

    with patch(
        "dfetch.commands.replay_patches.create_super_project", return_value=fake_super
    ):
        with patch("dfetch.commands.command.in_directory"):
            with patch(
                "dfetch.commands.replay_patches.create_sub_project",
                return_value=fake_sub,
            ):
                cmd(_make_args())

    fake_sub.update.assert_not_called()
    fake_super.add_path.assert_not_called()


def test_local_changes_logs_warning_and_skips():
    cmd = ReplayPatches()
    fake_super = _make_superproject(is_git=True, has_local_changes=True)
    fake_sub = _make_subproject()

    with patch(
        "dfetch.commands.replay_patches.create_super_project", return_value=fake_super
    ):
        with patch("dfetch.commands.command.in_directory"):
            with patch(
                "dfetch.commands.replay_patches.create_sub_project",
                return_value=fake_sub,
            ):
                cmd(_make_args())

    fake_sub.update.assert_not_called()
    fake_super.add_path.assert_not_called()


# ---------------------------------------------------------------------------
# Error scenarios
# ---------------------------------------------------------------------------


def test_no_vcs_superproject_raises():
    cmd = ReplayPatches()
    fake_super = Mock(spec=NoVcsSuperProject)

    with patch(
        "dfetch.commands.replay_patches.create_super_project", return_value=fake_super
    ):
        with pytest.raises(RuntimeError):
            cmd(_make_args())


def test_interactive_without_tty_raises():
    cmd = ReplayPatches()
    fake_super = _make_superproject(is_git=True)

    with patch(
        "dfetch.commands.replay_patches.create_super_project", return_value=fake_super
    ):
        with patch("dfetch.commands.replay_patches.is_tty", return_value=False):
            with pytest.raises(RuntimeError, match="interactive"):
                cmd(_make_args(interactive=True))


def test_negative_count_raises():
    cmd = ReplayPatches()
    fake_super = _make_superproject(is_git=True)

    with patch(
        "dfetch.commands.replay_patches.create_super_project", return_value=fake_super
    ):
        with pytest.raises(RuntimeError, match="--count must be >= 0"):
            cmd(_make_args(count=-1))


# ---------------------------------------------------------------------------
# project:N suffix (single project)
# ---------------------------------------------------------------------------


def test_single_project_suffix_becomes_count():
    cmd = ReplayPatches()
    fake_super = _make_superproject(is_git=True)
    fake_sub = _make_subproject()

    with patch(
        "dfetch.commands.replay_patches.create_super_project", return_value=fake_super
    ):
        with patch("dfetch.commands.command.in_directory"):
            with patch(
                "dfetch.commands.replay_patches.create_sub_project",
                return_value=fake_sub,
            ):
                with patch("dfetch.commands.replay_patches.is_tty", return_value=False):
                    cmd(_make_args(projects=["my_project:2"]))

    fake_sub.apply_patches.assert_called_once_with(2)


def test_count_and_suffix_raises():
    cmd = ReplayPatches()
    fake_super = _make_superproject(is_git=True)

    with patch(
        "dfetch.commands.replay_patches.create_super_project", return_value=fake_super
    ):
        with pytest.raises(RuntimeError, match="not both"):
            cmd(_make_args(projects=["my_project:2"], count=1))


# ---------------------------------------------------------------------------
# Combined multi-project path
# ---------------------------------------------------------------------------


def _make_multi_superproject(names):
    sp = Mock(spec=GitSuperProject)
    sp.manifest = mock_manifest([{"name": n} for n in names])
    sp.root_directory = Path("/tmp")
    sp.ignored_files.return_value = []
    sp.eol_preferences = Mock(return_value={})
    sp.has_local_changes_in_dir.return_value = False
    return sp


def _make_named_subproject(name, patches=None):
    sub = Mock()
    sub.patch = patches if patches is not None else [f"patches/{name}.patch"]
    sub.local_path = name
    sub.on_disk_version.return_value = "v1"
    with tempfile.NamedTemporaryFile(delete=False, suffix=".yaml", mode="wb") as f:
        f.write(b"dfetch:\n  patch: patches/a.patch\n")
        sub.metadata_path = f.name
    return sub


def test_combined_two_projects_all_patches():
    cmd = ReplayPatches()
    fake_super = _make_multi_superproject(["proj_a", "proj_b"])
    sub_a = _make_named_subproject("proj_a")
    sub_b = _make_named_subproject("proj_b")

    with patch(
        "dfetch.commands.replay_patches.create_super_project", return_value=fake_super
    ):
        with patch(
            "dfetch.commands.replay_patches.create_sub_project",
            side_effect=[sub_a, sub_b],
        ):
            with patch("dfetch.commands.replay_patches.is_tty", return_value=False):
                with patch("dfetch.commands.replay_patches.in_directory"):
                    cmd(_make_args())

    fake_super.add_path.assert_any_call("proj_a")
    fake_super.add_path.assert_any_call("proj_b")
    sub_a.apply_patches.assert_called_once_with(-1)
    sub_b.apply_patches.assert_called_once_with(-1)
    fake_super.restore_staged.assert_any_call("proj_a")
    fake_super.restore_staged.assert_any_call("proj_b")


def test_combined_per_project_counts():
    cmd = ReplayPatches()
    fake_super = _make_multi_superproject(["proj_a", "proj_b"])
    sub_a = _make_named_subproject("proj_a")
    sub_b = _make_named_subproject("proj_b")

    with patch(
        "dfetch.commands.replay_patches.create_super_project", return_value=fake_super
    ):
        with patch(
            "dfetch.commands.replay_patches.create_sub_project",
            side_effect=[sub_a, sub_b],
        ):
            with patch("dfetch.commands.replay_patches.is_tty", return_value=False):
                with patch("dfetch.commands.replay_patches.in_directory"):
                    cmd(_make_args(projects=["proj_a:0", "proj_b"]))

    sub_a.apply_patches.assert_called_once_with(0)
    sub_b.apply_patches.assert_called_once_with(-1)
    fake_super.restore_from_head.assert_called_once_with("proj_a")
    fake_super.restore_staged.assert_called_once_with("proj_b")


def test_combined_count_flag_raises():
    cmd = ReplayPatches()
    fake_super = _make_multi_superproject(["proj_a", "proj_b"])

    with patch(
        "dfetch.commands.replay_patches.create_super_project", return_value=fake_super
    ):
        with patch("dfetch.commands.replay_patches.in_directory"):
            with pytest.raises(RuntimeError, match="single-project"):
                cmd(_make_args(count=1))


def test_combined_interactive_launches_tui():
    cmd = ReplayPatches()
    fake_super = _make_multi_superproject(["proj_a", "proj_b"])
    sub_a = _make_named_subproject("proj_a")
    sub_b = _make_named_subproject("proj_b")

    with patch(
        "dfetch.commands.replay_patches.create_super_project", return_value=fake_super
    ):
        with patch(
            "dfetch.commands.replay_patches.create_sub_project",
            side_effect=[sub_a, sub_b],
        ):
            with patch("dfetch.commands.replay_patches.is_tty", return_value=True):
                with patch("dfetch.commands.replay_patches.in_directory"):
                    with patch(
                        "dfetch.commands.replay_patches._step_tui_multi"
                    ) as mock_tui:
                        cmd(_make_args(interactive=True))

    mock_tui.assert_called_once()
    states = mock_tui.call_args[0][0]
    assert [s.name for s in states] == ["proj_a", "proj_b"]
