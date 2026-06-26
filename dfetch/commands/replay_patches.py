"""Replaying patches interactively.

*Dfetch* allows you to keep local changes to external projects in the form of
patch files.  The ``replay-patches`` command lets you inspect what each patch
contributes by staging the clean upstream source in the git index and
optionally stepping the working tree through each patch in turn.

Because ``git diff`` always compares the working tree against the index, any
diff-aware editor will immediately show what the applied patches change
relative to the upstream source — no manual setup needed.

Run without arguments to replay all patches at once:

.. code-block:: console

   $ dfetch replay-patches some-project

Use ``--count`` to stop at a specific patch number, or ``--interactive`` to
step through the stack with the ← and → arrow keys.  In either case the
command always restores the original working tree and index before it exits —
no permanent changes are made.

.. tabs::

   .. tab:: Git

      .. scenario-include:: ../features/replay-patches-in-git.feature

   .. tab:: SVN

      .. scenario-include:: ../features/replay-patches-in-svn.feature
"""

import argparse
import dataclasses
import logging
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path

import dfetch.commands.command
import dfetch.manifest.project
from dfetch.log import get_logger
from dfetch.project import create_sub_project, create_super_project
from dfetch.project.gitsuperproject import GitSuperProject
from dfetch.project.subproject import SubProject
from dfetch.project.superproject import NoVcsSuperProject, SuperProject
from dfetch.terminal import BOLD, DIM, RESET, Screen, is_tty, read_key
from dfetch.util.cmdline import SubprocessCommandError
from dfetch.util.util import in_directory
from dfetch.vcs.patch import Patch

logger = get_logger(__name__)


@dataclasses.dataclass
class _ProjectState:
    """Tracks the current patch position for one project during a combined review."""

    name: str
    local_path: str
    patches: list[str]
    current: int = 0

    @property
    def fully_patched(self) -> bool:
        """Return True when all patches have been applied."""
        return self.current == len(self.patches)


def _parse_project_spec(spec: str) -> tuple[str, int | None]:
    """Split 'name:N' into (name, N); a bare name returns (name, None)."""
    if ":" not in spec:
        return spec, None
    name, _, tail = spec.rpartition(":")
    try:
        n = int(tail)
    except ValueError as exc:
        raise RuntimeError(
            f"invalid project spec {spec!r}; expected name or name:N"
        ) from exc
    if n < 0:
        raise RuntimeError(f"invalid project spec {spec!r}; patch count must be >= 0")
    return name, n


def _validate_superproject(superproject: SuperProject) -> None:
    if isinstance(superproject, NoVcsSuperProject):
        raise RuntimeError(
            "The project containing the manifest is not under version control,"
            " reviewing patches is not supported"
        )
    if not isinstance(superproject, GitSuperProject):
        logger.warning(
            "replay-patches has limited support in SVN superprojects"
            " (no staging area — use `svn diff` to inspect changes)"
        )


def _check_count_conflicts(
    count: int | None, per_project_counts: dict[str, int]
) -> None:
    if count is not None and per_project_counts:
        raise RuntimeError("use either --count or project:N, not both")


def _effective_count(
    count: int | None,
    selected: list[dfetch.manifest.project.ProjectEntry],
    per_project_counts: dict[str, int],
) -> int | None:
    """Return the effective patch count for single-project mode."""
    if count is not None or not selected:
        return count
    return per_project_counts.get(selected[0].name)


class ReplayPatches(dfetch.commands.command.Command):
    """Replay what patches contribute to a project.

    The ``replay-patches`` command stages the clean upstream source in the git
    index and applies the selected patches to the working tree, so ``git diff``
    shows exactly what the patches change relative to upstream.  Use
    ``--interactive`` to step through the stack patch-by-patch with ← and →.
    The command always restores the original state before it exits.
    """

    @staticmethod
    def create_menu(subparsers: dfetch.commands.command.SubparserActionType) -> None:
        """Add the menu for the replay-patches action."""
        parser = dfetch.commands.command.Command.parser(subparsers, ReplayPatches)
        parser.add_argument(
            "projects",
            metavar="<project>",
            type=str,
            nargs="*",
            help="Specific project(s) to review; append :N to limit patches (e.g. proj:2)",
        )
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--count",
            "-n",
            metavar="N",
            type=int,
            default=None,
            help="Number of patches to apply, single project only (default: all)",
        )
        group.add_argument(
            "--interactive",
            "-i",
            action="store_true",
            default=False,
            help="Step through patches interactively with ← and →",
        )

    def __call__(self, args: argparse.Namespace) -> None:
        """Perform the replay patches."""
        if args.count is not None and args.count < 0:
            raise RuntimeError("--count must be >= 0")

        superproject = create_super_project()
        _validate_superproject(superproject)

        if args.interactive and not is_tty():
            raise RuntimeError("--interactive requires an interactive terminal")

        project_names, per_project_counts = self._parse_project_args(args.projects)
        _check_count_conflicts(args.count, per_project_counts)

        selected = list(superproject.manifest.selected_projects(project_names))
        if len(selected) >= 2:
            with in_directory(superproject.root_directory):
                _review_projects_combined(
                    superproject,
                    selected,
                    per_project_counts,
                    args.count,
                    args.interactive,
                )
        else:
            count = _effective_count(args.count, selected, per_project_counts)
            self._iter_projects(
                superproject,
                project_names,
                lambda project: self._review_project(
                    superproject, project, count, args.interactive
                ),
            )

    @staticmethod
    def _parse_project_args(
        projects: list[str],
    ) -> tuple[list[str], dict[str, int]]:
        """Parse raw project arguments into names and per-project patch counts."""
        parsed = [_parse_project_spec(s) for s in projects]
        project_names = [name for name, _ in parsed]
        per_project_counts: dict[str, int] = {
            name: n for name, n in parsed if n is not None
        }
        return project_names, per_project_counts

    def _review_project(
        self,
        superproject: SuperProject,
        project: dfetch.manifest.project.ProjectEntry,
        count: int | None,
        interactive: bool,
    ) -> None:
        """Set up review state for a single project, then restore."""
        subproject = create_sub_project(project)
        git_super = superproject if isinstance(superproject, GitSuperProject) else None

        def _ignored() -> list[str]:
            return list(superproject.ignored_files(project.destination))

        if not _can_review_project(superproject, subproject, project.name):
            return

        saved_metadata = Path(subproject.metadata_path).read_bytes()
        total_patches = len(list(subproject.patch))
        chosen_count = count if count is not None else -1
        effective = (
            total_patches if chosen_count == -1 else min(chosen_count, total_patches)
        )
        diff_cmd = "`git diff`" if git_super is not None else "`svn diff`"
        info_msg = (
            f"stage = upstream, working tree = {effective} patch(es) applied"
            f" — open your editor and run {diff_cmd} to inspect"
        )
        worktree_fully_patched = False
        try:
            subproject.update(
                force=True,
                ignored_files_callback=_ignored,
                patch_count=0,
                eol_preferences_callback=superproject.eol_preferences,
            )
            if git_super is not None:
                git_super.add_path(subproject.local_path)
            worktree_fully_patched = _apply_review(
                subproject, project.name, chosen_count, interactive, info_msg
            )
        finally:
            try:
                _restore_project(
                    superproject,
                    git_super,
                    subproject,
                    project.name,
                    worktree_fully_patched,
                    _ignored,
                )
            finally:
                Path(subproject.metadata_path).write_bytes(saved_metadata)


def _can_review_project(
    superproject: SuperProject,
    subproject: SubProject,
    project_name: str,
) -> bool:
    """Return False and log a warning when the project cannot be reviewed."""
    if not subproject.patch:
        logger.print_warning_line(
            project_name,
            'skipped - there is no patch file, use "dfetch diff"'
            f" {project_name} to create one",
        )
        return False
    if not subproject.on_disk_version():
        logger.print_warning_line(
            project_name,
            f'skipped - the project was never fetched, use "dfetch update {project_name}"',
        )
        return False
    if superproject.has_local_changes_in_dir(subproject.local_path):
        logger.print_warning_line(
            project_name,
            f"skipped - uncommitted changes in {subproject.local_path}",
        )
        return False
    return True


def _apply_review(
    subproject: SubProject,
    project_name: str,
    chosen_count: int,
    interactive: bool,
    info_msg: str,
) -> bool:
    """Run the review session; return True when the worktree is already fully patched."""
    if interactive:
        _step_tui(list(subproject.patch), subproject.local_path, project_name)
        return False

    subproject.apply_patches(chosen_count)
    logger.print_info_line(project_name, info_msg)
    if is_tty():
        input("Press Enter to restore...")
    return chosen_count == -1


def _restore_project(
    superproject: SuperProject,
    git_super: GitSuperProject | None,
    subproject: SubProject,
    project_name: str,
    worktree_fully_patched: bool,
    ignored_callback: Callable[[], list[str]],
) -> None:
    """Restore the project to the fully-patched state and un-stage the index."""
    if git_super is not None:
        if worktree_fully_patched:
            git_super.restore_staged(subproject.local_path)
        else:
            git_super.restore_from_head(subproject.local_path)
    else:
        if not worktree_fully_patched:
            subproject.update(
                force=True,
                ignored_files_callback=ignored_callback,
                patch_count=0,
                eol_preferences_callback=superproject.eol_preferences,
            )
            subproject.apply_patches()
    logger.print_info_line(project_name, "restored")


# ---------------------------------------------------------------------------
# Combined multi-project path
# ---------------------------------------------------------------------------

_StagedEntry = tuple[SubProject, _ProjectState, bytes, Callable[[], list[str]]]


def _collect_reviewable(
    superproject: SuperProject,
    selected: list[dfetch.manifest.project.ProjectEntry],
) -> list[tuple[dfetch.manifest.project.ProjectEntry, SubProject]]:
    """Return (project, subproject) pairs that pass the can-review check."""
    result = []
    for project in selected:
        subproject = create_sub_project(project)
        if _can_review_project(superproject, subproject, project.name):
            result.append((project, subproject))
    return result


def _stage_one(
    superproject: SuperProject,
    git_super: GitSuperProject | None,
    project: dfetch.manifest.project.ProjectEntry,
    subproject: SubProject,
) -> _StagedEntry:
    """Fetch upstream into the worktree and stage it; return a restore tuple."""
    saved_metadata = Path(subproject.metadata_path).read_bytes()

    def _ignored() -> list[str]:
        return list(superproject.ignored_files(project.destination))

    try:
        subproject.update(
            force=True,
            ignored_files_callback=_ignored,
            patch_count=0,
            eol_preferences_callback=superproject.eol_preferences,
        )
        if git_super is not None:
            git_super.add_path(subproject.local_path)
    except Exception:
        Path(subproject.metadata_path).write_bytes(saved_metadata)
        raise
    state = _ProjectState(
        name=project.name,
        local_path=subproject.local_path,
        patches=list(subproject.patch),
    )
    return subproject, state, saved_metadata, _ignored


def _run_combined_review(
    staged: list[_StagedEntry],
    git_super: GitSuperProject | None,
    per_project_counts: dict[str, int],
    interactive: bool,
) -> None:
    """Apply patches and pause (non-interactive) or launch tree TUI (interactive)."""
    if interactive:
        _step_tui_multi([state for _, state, _, _ in staged])
        return
    diff_cmd = "`git diff`" if git_super is not None else "`svn diff`"
    for subproject, state, _, _ in staged:
        count = per_project_counts.get(state.name, -1)
        subproject.apply_patches(count)
        state.current = (
            len(state.patches) if count == -1 else min(count, len(state.patches))
        )
        logger.print_info_line(
            state.name,
            f"stage = upstream, working tree = {state.current} patch(es) applied"
            f" — open your editor and run {diff_cmd} to inspect",
        )
    if is_tty():
        input("Press Enter to restore...")


def _restore_one_combined(
    superproject: SuperProject,
    git_super: GitSuperProject | None,
    entry: _StagedEntry,
) -> None:
    """Restore a single staged project and write back its saved metadata."""
    subproject, state, saved_meta, ignored = entry
    try:
        _restore_project(
            superproject,
            git_super,
            subproject,
            state.name,
            state.fully_patched,
            ignored,
        )
    finally:
        Path(subproject.metadata_path).write_bytes(saved_meta)


def _review_projects_combined(
    superproject: SuperProject,
    selected: list[dfetch.manifest.project.ProjectEntry],
    per_project_counts: dict[str, int],
    count: int | None,
    interactive: bool,
) -> None:
    """Fetch + stage all projects, pause for review, then restore all."""
    if count is not None:
        raise RuntimeError(
            "--count is for single-project use; use project:N syntax for per-project counts"
        )
    git_super = superproject if isinstance(superproject, GitSuperProject) else None
    reviewable = _collect_reviewable(superproject, selected)
    if not reviewable:
        return
    staged: list[_StagedEntry] = []
    try:
        for project, subproject in reviewable:
            staged.append(_stage_one(superproject, git_super, project, subproject))
        _run_combined_review(staged, git_super, per_project_counts, interactive)
    finally:
        for entry in staged:
            try:
                _restore_one_combined(superproject, git_super, entry)
            except (RuntimeError, SubprocessCommandError, OSError) as exc:
                logger.print_error_line(entry[1].name, str(exc))


# ---------------------------------------------------------------------------
# Single-project TUI
# ---------------------------------------------------------------------------


def _draw_tui_frame(
    screen: Screen,
    patches: list[str],
    current: int,
    total: int,
    project_name: str,
) -> None:
    """Render the current patch-stack state to the screen."""
    count_label = str(current) if current < total else "all"
    lines: list[str] = [
        f"  {DIM}← → step    Enter restore and exit    Ctrl-C abort{RESET}",
        "  " + "─" * 54,
        f"  {project_name}  [{count_label}/{total} patches applied]",
    ]
    for idx, patch_name in enumerate(patches):
        marker = f"{BOLD}[x]{RESET}" if idx < current else f"{DIM}[ ]{RESET}"
        lines.append(f"    {marker} {patch_name}")
    screen.draw(lines)


@contextmanager
def _silent_patch_ng() -> Generator[None, None, None]:
    """Suppress patch_ng info logs so they don't corrupt the TUI frame."""
    patch_logger = logging.getLogger("patch_ng")
    prev = patch_logger.level
    patch_logger.setLevel(logging.CRITICAL)
    try:
        yield
    finally:
        patch_logger.setLevel(prev)


def _apply_step(
    key: str,
    current: int,
    total: int,
    patches: list[str],
    local_path: str,
) -> tuple[int, bool]:
    """Handle one keypress; return (new_current, done)."""
    if key == "LEFT" and current > 0:
        with _silent_patch_ng():
            Patch.from_file(patches[current - 1]).reverse().apply(root=local_path)
        return current - 1, False
    if key == "RIGHT" and current < total:
        with _silent_patch_ng():
            Patch.from_file(patches[current]).apply(root=local_path)
        return current + 1, False
    if key in ("ENTER", "ESC"):
        return current, True
    return current, False


def _step_tui(patches: list[str], local_path: str, project_name: str) -> None:
    """Interactive patch-stack stepper using arrow keys.

    The git index is staged once (clean upstream) before this function is
    called.  Only the working tree is updated on each step so that
    ``git diff`` always shows the contribution of the currently applied patches.
    Patches are applied or reversed directly — no VCS fetch per step.
    """
    total = len(patches)
    current = 0
    screen = Screen()

    while True:
        _draw_tui_frame(screen, patches, current, total, project_name)
        try:
            key = read_key()
        except KeyboardInterrupt:
            screen.clear()
            raise
        try:
            current, done = _apply_step(key, current, total, patches, local_path)
        except RuntimeError:
            screen.clear()
            raise
        if done:
            screen.clear()
            return


# ---------------------------------------------------------------------------
# Multi-project TUI
# ---------------------------------------------------------------------------


def _draw_tui_tree(
    screen: Screen,
    states: list[_ProjectState],
    focused: int,
) -> None:
    """Render the multi-project patch-stack tree to the screen."""
    lines: list[str] = [
        f"  {DIM}← → step    ↑ ↓ switch project    Enter restore and exit    Ctrl-C abort{RESET}",
        "  " + "─" * 71,
    ]
    for idx, state in enumerate(states):
        total = len(state.patches)
        count_label = str(state.current) if state.current < total else "all"
        prefix = ">" if idx == focused else " "
        lines.append(
            f"  {prefix} {state.name}  [{count_label}/{total} patches applied]"
        )
        for pidx, patch_name in enumerate(state.patches):
            marker = f"{BOLD}[x]{RESET}" if pidx < state.current else f"{DIM}[ ]{RESET}"
            lines.append(f"      {marker} {patch_name}")
    screen.draw(lines)


def _handle_tui_multi_key(
    key: str,
    focused: int,
    states: list[_ProjectState],
) -> tuple[int, bool]:
    """Handle one keypress in the multi-project TUI; return (new_focused, done)."""
    if key == "UP" and focused > 0:
        return focused - 1, False
    if key == "DOWN" and focused < len(states) - 1:
        return focused + 1, False
    state = states[focused]
    state.current, done = _apply_step(
        key, state.current, len(state.patches), state.patches, state.local_path
    )
    return focused, done


def _step_tui_multi(states: list[_ProjectState]) -> None:
    """Multi-project interactive TUI: ↑/↓ switch focus, ←/→ step patches."""
    focused = 0
    screen = Screen()
    while True:
        _draw_tui_tree(screen, states, focused)
        try:
            key = read_key()
        except KeyboardInterrupt:
            screen.clear()
            raise
        try:
            focused, done = _handle_tui_multi_key(key, focused, states)
        except RuntimeError:
            screen.clear()
            raise
        if done:
            screen.clear()
            return
