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
    def create_menu(subparsers: "argparse._SubParsersAction") -> None:
        """Add the menu for the update action."""
        parser = dfetch.commands.command.Command.parser(subparsers, Update)
        parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            help="Always perform update, ignoring version check or local changes.",
        )
        parser.add_argument(
            "--no-recommendations",
            "-N",
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
        with in_directory(os.path.dirname(path)):
            for project in manifest.selected_projects(args.projects):
                with catch_runtime_exceptions(exceptions) as exceptions:
                    dfetch.project.make(project).update(force=args.force)

                if not args.no_recommendations and os.path.isdir(project.destination):
                    with in_directory(project.destination):
                        check_child_manifests(manifest, project, path)

        if exceptions:
            raise RuntimeError("\n".join(exceptions))
