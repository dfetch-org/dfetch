"""*Dfetch* can freeze the current versions of the projects.

It will overwrite your current manifest.
"""

import argparse
import os
from typing import List

import dfetch.commands.command
import dfetch.manifest.project
from dfetch import DEFAULT_MANIFEST_NAME
from dfetch.log import get_logger
from dfetch.manifest.manifest import Manifest, get_manifest
from dfetch.manifest.project import ProjectEntry
from dfetch.util.util import catch_runtime_exceptions, in_directory

logger = get_logger(__name__)


class Freeze(dfetch.commands.command.Command):
    """Freeze the versions of the projects.

    Overwrite the manifest with one that has all version as they are on disk.
    """

    @staticmethod
    def create_menu(subparsers: "argparse._SubParsersAction") -> None:
        """Add the parser menu for this action."""
        dfetch.commands.command.Command.parser(subparsers, Freeze)

    def __call__(self, args: argparse.Namespace) -> None:
        """Perform the freeze."""
        del args  # unused

        manifest, path = get_manifest()

        exceptions: List[str] = []
        projects: List[ProjectEntry] = []

        with in_directory(os.path.dirname(path)):
            for project in manifest.projects:
                with catch_runtime_exceptions(exceptions) as exceptions:
                    on_disk_version = dfetch.project.make(project).on_disk_version()

                    if on_disk_version:
                        logger.info(f"Freezing {project.name} on {on_disk_version}")
                        project.set_version(on_disk_version)
                    else:
                        logger.warning(
                            f"{project.name} has no version on disk, first update it with dfetch update"
                        )

                    projects.append(project)

            manifest = Manifest(
                {"version": "0.0", "remotes": manifest.remotes, "projects": projects}
            )

            manifest.dump(DEFAULT_MANIFEST_NAME)
            logger.info(f"Updated manifest ({DEFAULT_MANIFEST_NAME}) in {os.getcwd()}")
