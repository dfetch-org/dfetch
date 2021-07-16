"""To check if your projects are up-to-date, you can let dfetch check it.

For each project the local version (based on tag or revision) will be compared against
the available version. If there are new versions available this will be shown.

.. uml:: /static/uml/check.puml

Child-manifests
~~~~~~~~~~~~~~~

It is possible that fetched projects have manifests of their own.
After these projects are fetched (with ``dfetch update``), the manifests are fetched as well
and will be checked. If you don't what this, you can prevent *Dfetch*
checking child-manifests with ``--non-recursive``.

.. note:: Any name or destination clashes are currently up to the user.

"""

import argparse
import os
from typing import List

import dfetch.commands.command
import dfetch.manifest.manifest
import dfetch.manifest.validate
import dfetch.project
from dfetch.log import get_logger
from dfetch.manifest.project import ProjectEntry
from dfetch.util.util import catch_runtime_exceptions, in_directory

logger = get_logger(__name__)


class Check(dfetch.commands.command.Command):
    """Check all projects for updates.

    Check all project to see if there are any new updates.
    """

    @staticmethod
    def create_menu(subparsers: "argparse._SubParsersAction") -> None:
        """Add the parser menu for this action."""
        parser = dfetch.commands.command.Command.parser(subparsers, Check)
        parser.add_argument(
            "--non-recursive",
            "-N",
            action="store_true",
            help="Don't recursively check for child manifests.",
        )
        parser.add_argument(
            "projects",
            metavar="<project>",
            type=str,
            nargs="*",
            help="Specific project(s) to check",
        )

    def __call__(self, args: argparse.Namespace) -> None:
        """Perform the check."""
        manifest, path = dfetch.manifest.manifest.get_manifest()

        with in_directory(os.path.dirname(path)):
            exceptions: List[str] = []
            for project in manifest.selected_projects(args.projects):
                with catch_runtime_exceptions(exceptions) as exceptions:
                    dfetch.project.make(project).check_for_update()

                if not args.non_recursive and os.path.isdir(project.destination):
                    with in_directory(project.destination):
                        exceptions += Check._check_child_manifests(project, path)

        if exceptions:
            raise RuntimeError("\n".join(exceptions))

    @staticmethod
    def _check_child_manifests(project: ProjectEntry, path: str) -> List[str]:
        exceptions: List[str] = []
        for (
            childmanifest,
            childpath,
        ) in dfetch.manifest.manifest.get_childmanifests(project, skip=[path]):
            with in_directory(os.path.dirname(childpath)):
                for childproject in childmanifest.projects:
                    with catch_runtime_exceptions(exceptions) as exceptions:
                        dfetch.project.make(childproject).check_for_update()
        return exceptions
