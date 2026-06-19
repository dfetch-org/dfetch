"""Reviewing patches interactively.

*Dfetch* allows you to keep local changes to external projects in the form of
patch files.  The ``review-patch`` command lets you inspect what each patch
contributes by staging the clean upstream source in the git index and
optionally stepping the working tree through each patch in turn.

Because ``git diff`` always compares the working tree against the index, any
diff-aware editor will immediately show what the applied patches change
relative to the upstream source — no manual setup needed.

Run without arguments to review all patches at once:

.. code-block:: console

   $ dfetch review-patch some-project

Use ``--count`` to stop at a specific patch number, or ``--interactive`` to
step through the stack with the ← and → arrow keys.  In either case the
command always restores the original working tree and index before it exits —
no permanent changes are made.

.. tabs::

   .. tab:: Git

      .. scenario-include:: ../features/review-patch-in-git.feature

   .. tab:: SVN

      .. scenario-include:: ../features/review-patch-in-svn.feature
"""

import argparse
from collections.abc import Callable

import dfetch.commands.command
import dfetch.manifest.project
from dfetch.log import get_logger
from dfetch.project import create_sub_project, create_super_project
from dfetch.project.gitsuperproject import GitSuperProject
from dfetch.project.subproject import SubProject
from dfetch.project.superproject import NoVcsSuperProject, SuperProject
from dfetch.terminal import BOLD, DIM, RESET, Screen, is_tty, read_key
from dfetch.vcs.patch import Patch

logger = get_logger(__name__)


class ReviewPatch(dfetch.commands.command.Command):
    """Review what patches contribute to a project.

    The ``review-patch`` command stages the clean upstream source in the git
    index and applies the selected patches to the working tree, so ``git diff``
    shows exactly what the patches change relative to upstream.  Use
    ``--interactive`` to step through the stack patch-by-patch with ← and →.
    The command always restores the original state before it exits.
    """

    @staticmethod
    def create_menu(subparsers: dfetch.commands.command.SubparserActionType) -> None:
        """Add the menu for the review-patch action."""
        parser = dfetch.commands.command.Command.parser(subparsers, ReviewPatch)
        parser.add_argument(
            "projects",
            metavar="<project>",
            type=str,
            nargs="*",
            help="Specific project(s) to review",
        )
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--count",
            "-n",
            metavar="N",
            type=int,
            default=None,
            help="Number of patches to apply (default: all)",
        )
        group.add_argument(
            "--interactive",
            "-i",
            action="store_true",
            default=False,
            help="Step through patches interactively with ← and →",
        )

    def __call__(self, args: argparse.Namespace) -> None:
        """Perform the review patch."""
        if args.count is not None and args.count < 0:
            raise RuntimeError("--count must be >= 0")

        superproject = create_super_project()

        if isinstance(superproject, NoVcsSuperProject):
            raise RuntimeError(
                "The project containing the manifest is not under version control,"
                " reviewing patches is not supported"
            )
        if not isinstance(superproject, GitSuperProject):
            logger.warning(
                "review-patch has limited support in SVN superprojects"
                " (no staging area — use `svn diff` to inspect changes)"
            )

        if args.interactive and not is_tty():
            raise RuntimeError("--interactive requires an interactive terminal")

        self._iter_projects(
            superproject,
            args.projects,
            lambda project: self._review_project(
                superproject, project, args.count, args.interactive
            ),
        )

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

        total_patches = len(list(subproject.patch))
        subproject.update(
            force=True,
            ignored_files_callback=_ignored,
            patch_count=0,
            eol_preferences_callback=superproject.eol_preferences,
        )

        if git_super is not None:
            git_super.add_path(subproject.local_path)

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
            worktree_fully_patched = _apply_review(
                subproject, project.name, chosen_count, interactive, info_msg
            )
        finally:
            _restore_project(
                superproject,
                git_super,
                subproject,
                project.name,
                worktree_fully_patched,
                _ignored,
            )


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
    if not worktree_fully_patched:
        if git_super is not None:
            git_super.restore_worktree(subproject.local_path)
        else:
            subproject.update(
                force=True,
                ignored_files_callback=ignored_callback,
                patch_count=0,
                eol_preferences_callback=superproject.eol_preferences,
            )
        subproject.apply_patches()
    if git_super is not None:
        git_super.restore_staged(subproject.local_path)
    logger.print_info_line(project_name, "restored")


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


def _apply_step(
    key: str,
    current: int,
    total: int,
    patches: list[str],
    local_path: str,
) -> tuple[int, bool]:
    """Handle one keypress; return (new_current, done)."""
    if key == "LEFT" and current > 0:
        Patch.from_file(patches[current - 1]).reverse().apply(root=local_path)
        return current - 1, False
    if key == "RIGHT" and current < total:
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
            return
        current, done = _apply_step(key, current, total, patches, local_path)
        if done:
            screen.clear()
            return
