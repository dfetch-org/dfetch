"""Remove projects from the manifest and delete their directories.

Use ``dfetch remove <project>`` to remove one or more projects.
See :ref:`remove-a-project` for the full guide.

.. scenario-include:: ../features/remove-project.feature

"""

import argparse
import shutil

import dfetch.commands.command
from dfetch.log import get_logger
from dfetch.manifest.manifest import RequestedProjectNotFoundError
from dfetch.project import create_super_project
from dfetch.project.superproject import NoVcsSuperProject
from dfetch.util.util import in_directory, safe_rm

logger = get_logger(__name__)


class Remove(dfetch.commands.command.Command):
    """Remove a project from the manifest and delete its directory.

    Edits the manifest in-place when the manifest lives inside a git or SVN
    superproject to preserve comments and layout. When the manifest is not
    inside version control, a ``.backup`` copy of the manifest is written
    before updating it.
    """

    @staticmethod
    def create_menu(subparsers: dfetch.commands.command.SubparserActionType) -> None:
        """Add the menu for the remove action."""
        parser = dfetch.commands.command.Command.parser(subparsers, Remove)
        parser.add_argument(
            "projects",
            metavar="<project>",
            type=str,
            nargs="+",
            help="Specific project(s) to remove",
        )

    def __call__(self, args: argparse.Namespace) -> None:
        """Perform the remove action."""
        superproject = create_super_project()
        make_backup = isinstance(superproject, NoVcsSuperProject)

        with in_directory(superproject.root_directory):
            manifest_path = superproject.manifest.path

            # Pre-validate all projects and collect their destinations
            projects_to_remove = []
            for project in args.projects:
                try:
                    project_entries = superproject.manifest.selected_projects([project])
                    destination = project_entries[0].destination
                    projects_to_remove.append((project, destination))
                except RequestedProjectNotFoundError:
                    logger.print_info_line(
                        project, f"project '{project}' not found in manifest"
                    )

            if not projects_to_remove:
                return  # Nothing to do

            # Create backup once if any projects will be removed
            if make_backup:
                shutil.copyfile(manifest_path, manifest_path + ".backup")

            # Remove all projects from manifest in-memory
            for project, _ in projects_to_remove:
                superproject.manifest.remove(project)

            # Persist the manifest changes
            superproject.manifest.dump()

            # Only after successful persistence, perform filesystem deletions and logging
            for project, destination in projects_to_remove:
                safe_rm(destination)
                logger.print_info_line(project, "removed")
