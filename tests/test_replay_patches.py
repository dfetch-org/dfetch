"""Test the replay-patches command."""

# mypy: ignore-errors
# flake8: noqa

import argparse
import tempfile
from pathlib import Path
from unittest.mock import ANY, Mock, patch

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
    """All patches are applied and the project is restored from HEAD for a git superproject."""
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
                    with patch(
                        "dfetch.commands.replay_patches._is_safe_patch_path",
                        return_value=True,
                    ):
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
    fake_super.restore_staged.assert_not_called()
    fake_super.restore_from_head.assert_called_once_with("my_project")


def test_review_count_1_uses_patch_count_1():
    """--count 1 limits apply_patches to exactly one patch."""
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
                    with patch(
                        "dfetch.commands.replay_patches._is_safe_patch_path",
                        return_value=True,
                    ):
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
    """SVN superproject emits a warning, skips git staging, and re-fetches to restore."""
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
                        with patch(
                            "dfetch.commands.replay_patches._is_safe_patch_path",
                            return_value=True,
                        ):
                            cmd(_make_args())

    mock_log.warning.assert_called_once()
    fake_super.add_path.assert_not_called()
    fake_super.restore_staged.assert_not_called()
    # Once to stage clean upstream for review, once to restore afterwards.
    assert fake_sub.update.call_count == 2
    fake_sub.update.assert_called_with(
        force=True,
        ignored_files_callback=ANY,
        patch_count=0,
        eol_preferences_callback=ANY,
    )
    fake_sub.apply_patches.assert_any_call(-1)
    fake_sub.apply_patches.assert_any_call()


# ---------------------------------------------------------------------------
# Skip scenarios
# ---------------------------------------------------------------------------


def test_no_patches_logs_warning_and_skips():
    """Projects with no patches log a warning and skip update/staging."""
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
    """Projects that have never been fetched log a warning and are skipped."""
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
    """Projects with local working-tree changes log a warning and are skipped."""
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


def test_missing_patch_logs_warning_and_skips():
    """A project with a missing or out-of-root patch is skipped before staging.

    ``apply_patches`` silently skips such a patch rather than raising, so
    reviewing the project anyway would understate how many patches actually
    applied and could hand ``Patch.from_file`` a bad path in interactive mode.
    """
    cmd = ReplayPatches()
    fake_super = _make_superproject(is_git=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
            fake_sub = _make_subproject(patches=["patches/missing.patch"])

            with patch(
                "dfetch.commands.replay_patches.create_super_project",
                return_value=fake_super,
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
    """A superproject with no VCS raises TypeError."""
    cmd = ReplayPatches()
    fake_super = Mock(spec=NoVcsSuperProject)

    with patch(
        "dfetch.commands.replay_patches.create_super_project", return_value=fake_super
    ):
        with pytest.raises(TypeError):
            cmd(_make_args())


def test_interactive_without_tty_raises():
    """--interactive without a TTY raises RuntimeError."""
    cmd = ReplayPatches()
    fake_super = _make_superproject(is_git=True)

    with patch(
        "dfetch.commands.replay_patches.create_super_project", return_value=fake_super
    ):
        with patch("dfetch.commands.replay_patches.is_tty", return_value=False):
            with pytest.raises(RuntimeError, match="interactive"):
                cmd(_make_args(interactive=True))


def test_negative_count_raises():
    """--count with a negative value raises RuntimeError."""
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
    """project:N suffix is parsed and forwarded as the patch count."""
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
                    with patch(
                        "dfetch.commands.replay_patches._is_safe_patch_path",
                        return_value=True,
                    ):
                        cmd(_make_args(projects=["my_project:2"]))

    fake_sub.apply_patches.assert_called_once_with(2)


def test_count_and_suffix_raises():
    """Combining --count and project:N suffix raises RuntimeError."""
    cmd = ReplayPatches()
    fake_super = _make_superproject(is_git=True)

    with patch(
        "dfetch.commands.replay_patches.create_super_project", return_value=fake_super
    ):
        with pytest.raises(RuntimeError, match="not both"):
            cmd(_make_args(projects=["my_project:2"], count=1))


def test_negative_project_suffix_raises():
    """project:-N suffix raises RuntimeError with a clear message."""
    cmd = ReplayPatches()
    fake_super = _make_superproject(is_git=True)

    with patch(
        "dfetch.commands.replay_patches.create_super_project", return_value=fake_super
    ):
        with pytest.raises(RuntimeError, match=">= 0"):
            cmd(_make_args(projects=["my_project:-1"]))


def test_project_suffix_and_interactive_raises():
    """project:N combined with --interactive raises RuntimeError.

    The interactive TUI lets the patch count be picked once it launches, so
    a project:N suffix would otherwise be silently ignored: _apply_review
    only forwards chosen_count to the non-interactive apply_patches() call.
    """
    cmd = ReplayPatches()
    fake_super = _make_superproject(is_git=True)

    with patch(
        "dfetch.commands.replay_patches.create_super_project", return_value=fake_super
    ):
        with patch("dfetch.commands.replay_patches.is_tty", return_value=True):
            with pytest.raises(RuntimeError, match="project:N is not supported"):
                cmd(_make_args(projects=["my_project:2"], interactive=True))


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
    """Combined mode applies all patches for each of two projects."""
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
                    with patch(
                        "dfetch.commands.replay_patches._is_safe_patch_path",
                        return_value=True,
                    ):
                        cmd(_make_args())

    fake_super.add_path.assert_any_call("proj_a")
    fake_super.add_path.assert_any_call("proj_b")
    sub_a.apply_patches.assert_called_once_with(-1)
    sub_b.apply_patches.assert_called_once_with(-1)
    fake_super.restore_staged.assert_not_called()
    fake_super.restore_from_head.assert_any_call("proj_a")
    fake_super.restore_from_head.assert_any_call("proj_b")


def test_combined_per_project_counts():
    """Combined mode respects per-project patch counts specified with project:N."""
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
                    with patch(
                        "dfetch.commands.replay_patches._is_safe_patch_path",
                        return_value=True,
                    ):
                        cmd(_make_args(projects=["proj_a:0", "proj_b"]))

    sub_a.apply_patches.assert_called_once_with(0)
    sub_b.apply_patches.assert_called_once_with(-1)
    fake_super.restore_staged.assert_not_called()
    fake_super.restore_from_head.assert_any_call("proj_a")
    fake_super.restore_from_head.assert_any_call("proj_b")


def test_combined_count_flag_raises():
    """--count in combined multi-project mode raises RuntimeError."""
    cmd = ReplayPatches()
    fake_super = _make_multi_superproject(["proj_a", "proj_b"])

    with patch(
        "dfetch.commands.replay_patches.create_super_project", return_value=fake_super
    ):
        with patch("dfetch.commands.replay_patches.in_directory"):
            with pytest.raises(RuntimeError, match="single-project"):
                cmd(_make_args(count=1))


def test_combined_interactive_launches_tui():
    """Combined interactive mode launches the multi-project TUI."""
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
                        with patch(
                            "dfetch.commands.replay_patches._is_safe_patch_path",
                            return_value=True,
                        ):
                            cmd(_make_args(interactive=True))

    mock_tui.assert_called_once()
    states = mock_tui.call_args[0][0]
    assert [s.name for s in states] == ["proj_a", "proj_b"]


def test_stage_one_restores_worktree_on_add_path_failure():
    """A failure in add_path() after update() still restores the worktree, not just metadata."""
    from dfetch.commands.replay_patches import _stage_one

    fake_super = _make_multi_superproject(["proj_a"])
    sub_a = _make_named_subproject("proj_a")
    project = fake_super.manifest.selected_projects(["proj_a"])[0]
    fake_super.add_path.side_effect = RuntimeError("index lock")

    with pytest.raises(RuntimeError, match="index lock"):
        _stage_one(fake_super, fake_super, project, sub_a)

    sub_a.update.assert_called_once()
    fake_super.restore_from_head.assert_called_once_with("proj_a")


def test_restore_one_combined_skips_metadata_write_on_restore_failure():
    """Metadata is left untouched (not falsely marked clean) when the restore itself fails."""
    from dfetch.commands.replay_patches import _ProjectState, _restore_one_combined

    fake_super = _make_multi_superproject(["proj_a"])
    sub_a = _make_named_subproject("proj_a")
    fake_super.restore_from_head.side_effect = RuntimeError("boom")
    staged_bytes = b"staged-state"
    Path(sub_a.metadata_path).write_bytes(staged_bytes)
    entry = (
        sub_a,
        _ProjectState(name="proj_a", local_path="proj_a", patches=sub_a.patch),
        b"original-state",
        list,
    )

    with pytest.raises(RuntimeError, match="boom"):
        _restore_one_combined(fake_super, fake_super, entry)

    assert Path(sub_a.metadata_path).read_bytes() == staged_bytes


def test_combined_restore_failure_raises_but_still_restores_every_project():
    """A restore failure for one project doesn't stop restoration of the others, and is reported."""
    cmd = ReplayPatches()
    fake_super = _make_multi_superproject(["proj_a", "proj_b"])
    sub_a = _make_named_subproject("proj_a")
    sub_b = _make_named_subproject("proj_b")
    fake_super.restore_from_head.side_effect = lambda path: (
        (_ for _ in ()).throw(RuntimeError("boom")) if path == "proj_a" else None
    )

    with patch(
        "dfetch.commands.replay_patches.create_super_project", return_value=fake_super
    ):
        with patch(
            "dfetch.commands.replay_patches.create_sub_project",
            side_effect=[sub_a, sub_b],
        ):
            with patch("dfetch.commands.replay_patches.is_tty", return_value=False):
                with patch("dfetch.commands.replay_patches.in_directory"):
                    with patch(
                        "dfetch.commands.replay_patches._is_safe_patch_path",
                        return_value=True,
                    ):
                        with pytest.raises(RuntimeError):
                            cmd(_make_args())

    fake_super.restore_from_head.assert_any_call("proj_a")
    fake_super.restore_from_head.assert_any_call("proj_b")


def test_is_safe_patch_path_rejects_missing_and_outside_root():
    """A missing patch, or one outside cwd, is rejected rather than handed to Patch.from_file."""
    from dfetch.commands.replay_patches import _is_safe_patch_path

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
            (Path(tmpdir) / "patches").mkdir()
            (Path(tmpdir) / "patches" / "real.patch").write_text("diff")

            assert _is_safe_patch_path("patches/real.patch") is True
            assert _is_safe_patch_path("patches/missing.patch") is False
            assert _is_safe_patch_path("../outside.patch") is False


def test_apply_step_skips_unsafe_patch_without_crashing():
    """RIGHT on a missing patch logs a warning, still advances, and does not raise."""
    from dfetch.commands.replay_patches import _apply_step

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
            current, done = _apply_step(
                "RIGHT", 0, 1, ["patches/missing.patch"], "some/local/path"
            )

    assert (current, done) == (1, False)
