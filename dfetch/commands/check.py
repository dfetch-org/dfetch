"""To check if your projects are up-to-date, you can let dfetch check it.

For each project the local revision will be compared against the available
revision on that branch. If there are new versions available this will be shown.
"""

import argparse
import os

import dfetch.commands.command
import dfetch.manifest.manifest
import dfetch.manifest.validate
import dfetch.project
import dfetch.util
from dfetch.log import get_logger

logger = get_logger(__name__)


class Check(dfetch.commands.command.Command):
    """Check all projects for updates.

    Check all project to see if there are any new updates.
    """

    @staticmethod
    def create_menu(subparsers: "argparse._SubParsersAction") -> None:
        """Add the parser menu for this action."""
        dfetch.commands.command.Command.parser(subparsers, Check)

    def __call__(self, args: argparse.Namespace) -> None:
        """Perform the check."""
        manifest, path = dfetch.manifest.manifest.get_manifest()

        with dfetch.util.util.in_directory(os.path.dirname(path)):
            exceptions = []
            for project in manifest.projects:
                try:
                    dfetch.project.make(project).check_for_update()
                except RuntimeError as exc:
                    exceptions += [str(exc)]

        if exceptions:
            raise RuntimeError("\n".join(exceptions))
