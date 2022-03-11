"""Update is the main functionality of dfetch.

You can add Projects to your :ref:`Manifest` and update will fetch the version specified.
It tries to determine what kind of vcs it is: git, svn or something else.

.. uml:: /static/uml/update.puml

Child-manifests
~~~~~~~~~~~~~~~

It is possible that fetched projects have manifests of their own.
When these projects are fetched (with ``dfetch update``), the manifests are read as well
and will be checked to look for further dependencies. If you don't what recommendations, you can prevent *Dfetch*
checking child-manifests with ``--no-recommendations``.

"""

import argparse
import os
from typing import Any  # pylint: disable=unused-import
from typing import List

import dfetch.commands.command
import dfetch.manifest.manifest
import dfetch.manifest.project
import dfetch.manifest.validate
import dfetch.project.git
import dfetch.project.svn
from dfetch.commands.common import check_child_manifests
from dfetch.log import get_logger
from dfetch.util.util import catch_runtime_exceptions, in_directory

logger = get_logger(__name__)


class Update(dfetch.commands.command.Command):
    """Update all modules from the manifest.

    Verifies the manifest and checks all dependencies if updates are available.
    """

    @staticmethod
    def create_menu(subparsers: "argparse._SubParsersAction[Any]") -> None:
        """Add the menu for the update action."""
        parser = dfetch.commands.command.Command.parser(subparsers, Update)
        parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            help="Always perform update, ignoring version check or local changes.",
        )
        parser.add_argument(
            "-N",
            "--no-recommendations",
            action="store_true",
            help="Ignore recommendations from fetched projects.",
        )
        parser.add_argument(
            "projects",
            metavar="<project>",
            type=str,
            nargs="*",
            help="Specific project(s) to update",
        )

    def __call__(self, args: argparse.Namespace) -> None:
        """Perform the update."""
        manifest, path = dfetch.manifest.manifest.get_manifest()

        exceptions: List[str] = []
        destinations: List[str] = [
            os.path.realpath(project.destination) for project in manifest.projects
        ]
        with in_directory(os.path.dirname(path)):
            for project in manifest.selected_projects(args.projects):
                with catch_runtime_exceptions(exceptions) as exceptions:
                    self._check_destination(project, destinations)
                    dfetch.project.make(project).update(force=args.force)

                    if not args.no_recommendations and os.path.isdir(
                        project.destination
                    ):
                        with in_directory(project.destination):
                            check_child_manifests(manifest, project, path)

        if exceptions:
            raise RuntimeError("\n".join(exceptions))

    @staticmethod
    def _check_destination(
        project: dfetch.manifest.project.ProjectEntry, destinations: List[str]
    ) -> None:
        """Do some sanity checks on the destination path."""
        real_path = os.path.realpath(project.destination)
        cwd = os.getcwd()

        Update._check_path_traversal(project, real_path, cwd)
        Update._check_dst_not_in_blacklist(project, real_path, cwd)
        Update._check_overlapping_destination(project, destinations, real_path)
        Update._check_casing_mismatch(project, real_path)

    @staticmethod
    def _check_path_traversal(
        project: dfetch.manifest.project.ProjectEntry, real_path: str, safe_dir: str
    ) -> None:
        """Check if destination is outside the directory tree."""
        if os.path.commonprefix((real_path, safe_dir)) != safe_dir:
            # See https://owasp.org/www-community/attacks/Path_Traversal
            logger.print_warning_line(
                project.name,
                f'Skipping, path "{project.destination}" is outside manifest directory tree.',
            )
            raise RuntimeError(
                "Destination must be in the manifests folder or a subfolder. "
                f'"{project.destination}" is outside this tree!'
            )

    @staticmethod
    def _check_dst_not_in_blacklist(
        project: dfetch.manifest.project.ProjectEntry, real_path: str, safe_dir: str
    ) -> None:
        """Check if destination is in blacklist."""
        if real_path in [safe_dir]:
            logger.print_warning_line(
                project.name,
                f'Skipping, path "{project.destination}" is not allowed as destination.',
            )
            raise RuntimeError(
                "Destination must be in a valid subfolder. "
                f'"{project.destination}" is not valid!'
            )

    @staticmethod
    def _check_overlapping_destination(
        project: dfetch.manifest.project.ProjectEntry,
        destinations: List[str],
        real_path: str,
    ) -> None:
        """Check if project will try to write to the same destination."""
        common_prefixes = [
            os.path.commonprefix((real_path, dst))
            for dst in destinations
            if dst != real_path
        ]
        if destinations.count(real_path) > 1 or real_path in common_prefixes:
            logger.print_warning_line(
                project.name,
                f'Skipping due to overlapping destination: "{project.destination}"',
            )
            raise RuntimeError(
                f'There is already a project in "{project.destination}" or one of its subfolders!\n'
                "Each destination must be unique and not overlapping."
            )

    @staticmethod
    def _check_casing_mismatch(
        project: dfetch.manifest.project.ProjectEntry, real_path: str
    ) -> None:
        """Check if casing of destination match."""
        parent_folder, folder_name = os.path.dirname(real_path), os.path.basename(
            real_path
        )

        if os.path.exists(real_path) and folder_name not in os.listdir(parent_folder):
            logger.print_warning_line(
                project.name,
                f'Skipping due to casing mismatch between path on system and destination "{project.destination}"',
            )
            raise RuntimeError(
                f'The destination "{project.destination}" in the manifest has a different casing than on disk.\n'
                "On case-insensitive file systems (e.g. Windows), having this will give unexpected results."
            )
