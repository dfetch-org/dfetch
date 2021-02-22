"""To check if your projects are up-to-date, you can let dfetch check it.

For each project the local version (based on tag or revision) will be compared against
the available version. If there are new versions available this will be shown.

.. uml:: /static/uml/check.puml

"""

import argparse
import os
from typing import List

import dfetch.commands.command
import dfetch.manifest.manifest
import dfetch.manifest.validate
import dfetch.project
from dfetch.log import get_logger
from dfetch.util.util import catch_runtime_exceptions, in_directory

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

        with in_directory(os.path.dirname(path)):
            exceptions: List[str] = []
            for project in manifest.projects:
                with catch_runtime_exceptions(exceptions) as exceptions:
                    dfetch.project.make(project).check_for_update()

        if exceptions:
            raise RuntimeError("\n".join(exceptions))
