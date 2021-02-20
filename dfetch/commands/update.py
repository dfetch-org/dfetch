"""Update is the main functionality of dfetch.

You can add Projects to your :ref:`Manifest` and update will fetch the version specified.
It tries to determine what kind of vcs it is: git, svn or something else.

.. uml:: /static/uml/update.puml
"""

import argparse
import os
from typing import List

import dfetch.commands.command
import dfetch.manifest.manifest
import dfetch.manifest.project
import dfetch.manifest.validate
import dfetch.project.git
import dfetch.project.svn
from dfetch.log import get_logger
from dfetch.util.util import catch_runtime_exceptions, in_directory

logger = get_logger(__name__)


class Update(dfetch.commands.command.Command):
    """Update all modules from the manifest.

    Verifies the manifest and checks all dependencies if updates are available.
    """

    @staticmethod
    def create_menu(subparsers: "argparse._SubParsersAction") -> None:
        """Add the menu for the update action."""
        parser = dfetch.commands.command.Command.parser(subparsers, Update)
        parser.add_argument("--dry-run", "-n", action="store_true", help="Only check")

    def __call__(self, args: argparse.Namespace) -> None:
        """Perform the update."""
        manifest, path = dfetch.manifest.manifest.get_manifest()

        exceptions: List[str] = []
        with in_directory(os.path.dirname(path)):
            for project in manifest.projects:
                with catch_runtime_exceptions(exceptions) as exceptions:
                    dfetch.project.make(project).update()

                for submanifest, subpath in dfetch.manifest.manifest.get_submanifests(
                    project, skip=[path]
                ):
                    with in_directory(os.path.dirname(subpath)):
                        for subproject in submanifest.projects:
                            with catch_runtime_exceptions(exceptions) as exceptions:
                                dfetch.project.make(subproject).update()

        if exceptions:
            raise RuntimeError("\n".join(exceptions))
