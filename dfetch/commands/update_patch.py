"""Update is the main functionality of dfetch.

You can add Projects to your :ref:`Manifest` and update will fetch the version specified.
It tries to determine what kind of vcs it is: git, svn or something else.

"""

import argparse
import pathlib
import shutil

import dfetch.commands.command
import dfetch.manifest.project
import dfetch.project
from dfetch.log import get_logger
from dfetch.project.superproject import SuperProject
from dfetch.util.util import catch_runtime_exceptions, in_directory

logger = get_logger(__name__)


class UpdatePatch(dfetch.commands.command.Command):
    """Update a patch to reflect the last changes.

    Some stuff
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
                            f'skipped - there is no patch file, use "dfetch diff {project.name}" instead',
                        )
                        return

                    # Check if the project was ever fetched
                    on_disk_version = subproject.on_disk_version()
                    if not on_disk_version:
                        logger.print_warning_line(
                            project.name,
                            f'skipped - the project was never fetched before, use "dfetch update {project.name}"',
                        )
                        return

                    # Make sure no uncommitted changes (don't care about ignored files)
                    if subproject._are_there_local_changes(files_to_ignore):
                        logger.print_warning_line(
                            project.name,
                            "skipped - local changes after last update (use --force to overwrite)",
                        )
                        return

                    # Select patch to overwrite & make backup
                    patch_to_update = subproject.patch[-1]
                    shutil.move(patch_to_update, patch_to_update + ".backup")

                    # force update to fetched version from metadata without applying patch
                    subproject.update(
                        force=True,
                        files_to_ignore=files_to_ignore,
                        patch_count=len(subproject.patch) - 1,
                    )

                    # generate reverse patch
                    patch_text = subproject.diff(
                        old_revision=subproject.metadata_revision(),
                        new_revision="",
                        # ignore=files_to_ignore,
                        reverse=True,
                    )

                    if patch_text:
                        patch_path = pathlib.Path(patch_to_update)
                        logger.print_info_line(
                            project.name, f"Updating patch {patch_to_update}"
                        )
                        patch_path.write_text(patch_text, encoding="UTF-8")
                    else:
                        logger.print_info_line(
                            project.name,
                            f"No diffs found, kept patch {patch_to_update} unchanged",
                        )

                    # force update again to fetched version from metadata but with applying patch
                    subproject.update(
                        force=True, files_to_ignore=files_to_ignore, patch_count=-1
                    )

        if exceptions:
            raise RuntimeError("\n".join(exceptions))
