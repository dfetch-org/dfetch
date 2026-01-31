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

The existing patch is backed up before being overwritten.

The below statement will update the patch for ``some-project`` from your manifest.

.. code-block:: sh

   dfetch update-patch some-project

.. tabs::

   .. tab:: Git

      .. scenario-include:: ../features/update-patch-in-git.feature

   .. tab:: SVN

      .. scenario-include:: ../features/update-patch-in-svn.feature
"""

import argparse
import pathlib
import shutil
from typing import Optional

import dfetch.commands.command
import dfetch.manifest.project
import dfetch.project
from dfetch.log import get_logger
from dfetch.project.superproject import SuperProject
from dfetch.util.util import catch_runtime_exceptions, in_directory

logger = get_logger(__name__)


class UpdatePatch(dfetch.commands.command.Command):
    """Update a patch to reflect the last changes.

    The ``update-patch`` command regenerates the last patch of one or
    more projects based on the current working tree. This is useful
    when you have modified a project after applying a patch and want
    to record those changes in an updated patch file. If there is no
    patch yet, use ``dfetch diff`` instead.
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

    def __call__(self, args: argparse.Namespace) -> None:
        """Perform the update patch."""
        superproject = SuperProject()

        exceptions: list[str] = []

        if not superproject.in_vcs():
            raise RuntimeError(
                "The project containing the manifest is not under version control,"
                " updating patches is not supported"
            )

        with in_directory(superproject.root_directory):
            for project in superproject.manifest.selected_projects(args.projects):
                with catch_runtime_exceptions(exceptions) as exceptions:
                    subproject = dfetch.project.make(project)

                    files_to_ignore = superproject.ignored_files(project.destination)

                    # Check if the project has a patch, maybe suggest creating one?
                    if not subproject.patch:
                        logger.print_warning_line(
                            project.name,
                            f'skipped - there is no patch file, use "dfetch diff {project.name}"'
                            " to generate one instead",
                        )
                        continue

                    # Check if the project was ever fetched
                    on_disk_version = subproject.on_disk_version()
                    if not on_disk_version:
                        logger.print_warning_line(
                            project.name,
                            f'skipped - the project was never fetched before, use "dfetch update {project.name}"',
                        )
                        continue

                    # Make sure no uncommitted changes (don't care about ignored files)
                    if superproject.has_local_changes_in_dir(subproject.local_path):
                        logger.print_warning_line(
                            project.name,
                            f"skipped - Uncommitted changes in {subproject.local_path}",
                        )
                        continue

                    # force update to fetched version from metadata without applying patch
                    subproject.update(
                        force=True,
                        files_to_ignore=files_to_ignore,
                        patch_count=len(subproject.patch) - 1,
                    )

                    # generate reverse patch
                    patch_text = subproject.diff(
                        old_revision=superproject.current_revision(),
                        new_revision="",
                        # ignore=files_to_ignore,
                        reverse=True,
                    )

                    # Select patch to overwrite & make backup
                    if not self._update_patch(
                        subproject.patch[-1],
                        superproject.root_directory,
                        project.name,
                        patch_text,
                    ):
                        continue

                    # force update again to fetched version from metadata but with applying patch
                    subproject.update(
                        force=True, files_to_ignore=files_to_ignore, patch_count=-1
                    )

        if exceptions:
            raise RuntimeError("\n".join(exceptions))

    def _update_patch(
        self,
        patch_to_update: str,
        root: pathlib.Path,
        project_name: str,
        patch_text: str,
    ) -> Optional[pathlib.Path]:
        """Update the specified patch file with new patch text."""
        patch_path = pathlib.Path(patch_to_update).resolve()

        try:
            patch_path.relative_to(root)
        except ValueError:
            logger.print_warning_line(
                project_name,
                f'No updating patch "{patch_to_update}" which is outside {root}',
            )
            return None

        if patch_text:
            shutil.move(patch_to_update, patch_to_update + ".backup")
            logger.print_info_line(project_name, f'Updating patch "{patch_to_update}"')
            patch_path.write_text(patch_text, encoding="UTF-8")
        else:
            logger.print_info_line(
                project_name,
                f"No diffs found, kept patch {patch_to_update} unchanged",
            )
        return patch_path
