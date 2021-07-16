"""Update is the main functionality of dfetch.

You can add Projects to your :ref:`Manifest` and update will fetch the version specified.
It tries to determine what kind of vcs it is: git, svn or something else.

.. uml:: /static/uml/update.puml

Child-manifests
~~~~~~~~~~~~~~~

It is possible that projects have manifests of their own.
After the projects of the main manifest are fetched,
*Dfetch* will look for new manifests and update these as well following the same logic as above.
If you don't what this, you can prevent *Dfetch*
checking child-manifests with ``--non-recursive``.

.. note:: Any name or destination clashes are currently up to the user.

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
from dfetch.manifest.project import ProjectEntry
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
            "-N",
            "--non-recursive",
            action="store_true",
            help="Don't recursively check for child manifests.",
        )
        parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            help="Always perform update, ignoring version check or local changes.",
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

                if not args.non_recursive and os.path.isdir(project.destination):
                    with in_directory(project.destination):
                        exceptions += Update.__update_child_manifests(
                            project, path, force=args.force
                        )

        if exceptions:
            raise RuntimeError("\n".join(exceptions))

    @staticmethod
    def __update_child_manifests(
        project: ProjectEntry, path: str, force: bool = False
    ) -> List[str]:
        exceptions: List[str] = []
        for (
            childmanifest,
            childpath,
        ) in dfetch.manifest.manifest.get_childmanifests(project, skip=[path]):
            with in_directory(os.path.dirname(childpath)):
                for childproject in childmanifest.projects:
                    with catch_runtime_exceptions(exceptions) as exceptions:
                        dfetch.project.make(childproject).update(force)
        return exceptions
