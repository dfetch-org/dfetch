"""Updating patches.

*Dfetch* allows you to keep local changes to external projects in the form of
patch files. When those local changes evolve over time, an existing patch can
be updated to reflect the new state of the project.

The ``update-patch`` command automates the otherwise manual process of
refreshing a patch. It safely regenerates the last patch of a project based on
the current working tree, while keeping the upstream revision unchanged.

This command operates on projects defined in the :ref:`Manifest` and requires
that the manifest itself is located inside a version-controlled repository
(the *superproject*). The version control system of the superproject is used to
calculate and regenerate the patch.

The below statement will update the patch for ``some-project`` from your manifest.

.. code-block:: console

   $ dfetch update-patch some-project

.. tabs::

   .. tab:: Git

      .. scenario-include:: ../features/update-patch-in-git.feature

   .. tab:: SVN

      .. scenario-include:: ../features/update-patch-in-svn.feature

Targeting a patch in the middle of a stack
===========================================

When a project carries a stack of several patches, a local change may belong
to an earlier patch rather than the last one. Use ``--patch`` to record the
current change into that patch instead, so the stack keeps its
concern-per-patch structure:

.. code-block:: console

   $ dfetch update-patch some-project --patch 2
   $ dfetch update-patch some-project --patch 0002-swap-logging-backend

The target can be given as a 1-based index into the stack, or as a (partial)
patch file name. Any later patches are re-applied on top of the newly
recorded one, so they keep their own content unchanged whenever possible. If
a later patch no longer applies cleanly - because it genuinely depends on the
lines you changed - the project is restored to its previous state and the
conflict is reported, rather than silently folded into the wrong patch.

This is currently only supported for git superprojects.

.. scenario-include:: ../features/update-patch-intermediate-in-git.feature
"""

import argparse
import pathlib
from collections.abc import Callable, Sequence

import dfetch.commands.command
import dfetch.manifest.project
import dfetch.project
from dfetch.log import get_logger
from dfetch.project import create_super_project
from dfetch.project.gitsuperproject import GitSuperProject
from dfetch.project.metadata import Metadata
from dfetch.project.subproject import SubProject
from dfetch.project.superproject import NoVcsSuperProject, RevisionRange, SuperProject
from dfetch.util.util import check_no_path_traversal
from dfetch.vcs.patch import Patch

logger = get_logger(__name__)

IgnoredCallback = Callable[[], list[str]]


class UpdatePatch(dfetch.commands.command.Command):
    """Update a patch to reflect the last changes.

    The ``update-patch`` command regenerates the last patch of one or
    more projects based on the current working tree. This is useful
    when you have modified a project after applying a patch and want
    to record those changes in an updated patch file. If there is no
    patch yet, use ``dfetch diff`` instead.

    Use ``--patch`` to target an earlier patch in a project's patch
    stack instead; later patches are rebased on top of it.
    """

    @staticmethod
    def create_menu(subparsers: dfetch.commands.command.SubparserActionType) -> None:
        """Add the menu for the update-patch action."""
        parser = dfetch.commands.command.Command.parser(subparsers, UpdatePatch)
        parser.add_argument(
            "projects",
            metavar="<project>",
            type=str,
            nargs="*",
            help="Specific project(s) to update",
        )
        parser.add_argument(
            "--patch",
            metavar="<index|patch-name>",
            type=str,
            default=None,
            help=(
                "Record the change into this patch instead of the last one"
                " (1-based index, or a (partial) patch file name); later"
                " patches are rebased on top. Requires a single project."
            ),
        )

    def __call__(self, args: argparse.Namespace) -> None:
        """Perform the update patch."""
        superproject = create_super_project()

        if isinstance(superproject, NoVcsSuperProject):
            raise TypeError(
                "The project containing the manifest is not under version control,"
                " updating patches is not supported"
            )
        if not isinstance(superproject, GitSuperProject):
            logger.warning("Update patch is only fully supported in git superprojects!")

        if args.patch is not None and len(args.projects) != 1:
            raise RuntimeError("--patch requires exactly one project")

        self._iter_projects(
            superproject,
            args.projects,
            lambda project: self._process_project(superproject, project, args.patch),
        )

    def _process_project(
        self,
        superproject: SuperProject,
        project: dfetch.manifest.project.ProjectEntry,
        patch_target: str | None,
    ) -> None:
        """Perform the patch update for a single project."""
        subproject = dfetch.project.create_sub_project(project)
        destination = project.destination

        def _ignored(dst: str = destination) -> list[str]:
            return list(superproject.ignored_files(dst))

        if not self._can_update(subproject, project.name):
            return

        if superproject.has_local_changes_in_dir(subproject.local_path):
            logger.print_warning_line(
                project.name,
                f"skipped - Uncommitted changes in {subproject.local_path}",
            )
            return

        patches = list(subproject.patch)
        target_index = len(patches) - 1
        if patch_target is not None:
            resolved = _resolve_patch_index(patches, patch_target, project.name)
            if resolved is None:
                return
            target_index = resolved

        if target_index == len(patches) - 1:
            self._update_last_patch(superproject, subproject, project, _ignored)
            return

        if not isinstance(superproject, GitSuperProject):
            logger.print_warning_line(
                project.name,
                "skipped - targeting an intermediate patch requires a git superproject",
            )
            return

        self._update_intermediate_patch(
            superproject, subproject, project, _ignored, target_index
        )

    @staticmethod
    def _can_update(subproject: SubProject, project_name: str) -> bool:
        """Check the preconditions shared by both update paths."""
        if not subproject.patch:
            logger.print_warning_line(
                project_name,
                f'skipped - there is no patch file, use "dfetch diff {project_name}"'
                " to generate one instead",
            )
            return False

        if not subproject.on_disk_version():
            logger.print_warning_line(
                project_name,
                f'skipped - the project was never fetched before, use "dfetch update {project_name}"',
            )
            return False
        return True

    def _update_last_patch(
        self,
        superproject: SuperProject,
        subproject: SubProject,
        project: dfetch.manifest.project.ProjectEntry,
        ignored_callback: IgnoredCallback,
    ) -> None:
        """Regenerate the last patch of the stack from the working tree."""
        # force update to fetched version from metadata without applying patch
        subproject.update(
            force=True,
            ignored_files_callback=ignored_callback,
            patch_count=len(subproject.patch) - 1,
            eol_preferences_callback=superproject.eol_preferences,
        )

        # generate reverse patch
        patch_text = superproject.diff(
            subproject.local_path,
            revisions=RevisionRange("", ""),
            ignore=(Metadata.FILENAME,),
            reverse=True,
        )

        # Select patch to overwrite & make backup
        if not self._update_patch(
            subproject.patch[-1],
            superproject.root_directory,
            project.name,
            patch_text,
        ):
            return

        # force update again to fetched version from metadata but with applying patch
        subproject.update(
            force=True,
            ignored_files_callback=ignored_callback,
            patch_count=-1,
            eol_preferences_callback=superproject.eol_preferences,
        )

    def _update_intermediate_patch(
        self,
        git_super: GitSuperProject,
        subproject: SubProject,
        project: dfetch.manifest.project.ProjectEntry,
        ignored_callback: IgnoredCallback,
        target_index: int,
    ) -> None:
        """Record the working-tree change into an earlier patch, rebasing the rest.

        Peels the patches after ``target_index`` off the working tree (using
        their stored patch files, not a fetch), so the change can be isolated
        and recorded into the target patch on its own. The later patches are
        then re-applied unchanged on top; if one of them no longer applies,
        the project is restored from HEAD and the conflict is reported.
        """
        patches = list(subproject.patch)
        target_patch = patches[target_index]

        try:
            _peel_patches(subproject.local_path, patches[target_index + 1 :])
        except RuntimeError as exc:
            git_super.restore_from_head(subproject.local_path)
            raise RuntimeError(
                f'Could not isolate "{target_patch}": {exc}. It likely conflicts'
                " with the change you're recording; resolve it manually or target"
                " a later patch instead. The project was restored to its previous"
                " state."
            ) from exc

        git_super.add_path(subproject.local_path)
        try:
            subproject.update(
                force=True,
                ignored_files_callback=ignored_callback,
                patch_count=target_index,
                eol_preferences_callback=git_super.eol_preferences,
            )
            patch_text = git_super.diff(
                subproject.local_path,
                revisions=RevisionRange("", ""),
                ignore=(Metadata.FILENAME,),
                reverse=True,
            )
        finally:
            git_super.restore_staged(subproject.local_path)

        if not self._update_patch(
            target_patch, git_super.root_directory, project.name, patch_text
        ):
            return

        try:
            subproject.update(
                force=True,
                ignored_files_callback=ignored_callback,
                patch_count=-1,
                eol_preferences_callback=git_super.eol_preferences,
            )
        except RuntimeError as exc:
            git_super.restore_from_head(subproject.local_path)
            raise RuntimeError(
                f'Patch "{target_patch}" was updated, but a later patch no longer'
                f" applies on top of it ({exc}). The project was restored to its"
                " previous state; resolve the conflict manually or target the"
                " conflicting patch instead."
            ) from exc

    def _update_patch(
        self,
        patch_to_update: str,
        root: pathlib.Path,
        project_name: str,
        patch_text: str,
    ) -> pathlib.Path | None:
        """Update the specified patch file with new patch text."""
        patch_path = pathlib.Path(patch_to_update).resolve()

        try:
            check_no_path_traversal(patch_path, root)
        except RuntimeError:
            logger.print_warning_line(
                project_name,
                f'No updating patch "{patch_to_update}" which is outside {root}',
            )
            return None

        if patch_text:
            logger.print_info_line(project_name, f'Updating patch "{patch_to_update}"')
            patch_path.write_text(patch_text, encoding="UTF-8")
        else:
            logger.print_info_line(
                project_name,
                f"No diffs found, kept patch {patch_to_update} unchanged",
            )
        return patch_path


def _peel_patches(local_path: str, patches_to_peel: Sequence[str]) -> None:
    """Reverse-apply the given patches, from last to first, onto the working tree."""
    for patch in reversed(patches_to_peel):
        try:
            Patch.from_file(patch).reverse().apply(root=local_path)
        except OSError as exc:
            raise RuntimeError(f'reversing "{patch}" failed: {exc}') from exc


def _resolve_patch_index(
    patches: list[str], target: str, project_name: str
) -> int | None:
    """Resolve a --patch argument to an index into the patch stack, or None if invalid."""
    if target.isdigit():
        index = int(target) - 1
        if 0 <= index < len(patches):
            return index
        logger.print_warning_line(
            project_name,
            f"skipped - --patch {target} is out of range,"
            f" project has {len(patches)} patch(es)",
        )
        return None

    matches = [
        i for i, patch in enumerate(patches) if _patch_name_matches(patch, target)
    ]
    if len(matches) == 1:
        return matches[0]

    available = ", ".join(pathlib.Path(patch).name for patch in patches)
    if not matches:
        logger.print_warning_line(
            project_name,
            f'skipped - no patch matches "{target}", available: {available}',
        )
    else:
        logger.print_warning_line(
            project_name,
            f'skipped - "{target}" matches multiple patches ({available}),'
            " be more specific",
        )
    return None


def _patch_name_matches(patch_path: str, target: str) -> bool:
    """Check if a patch's file name matches a --patch target string."""
    name = pathlib.Path(patch_path).name
    stem = pathlib.Path(patch_path).stem
    return target in (name, stem) or name.startswith(target) or stem.startswith(target)
