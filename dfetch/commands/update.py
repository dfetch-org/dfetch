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
            "--non-recursive",
            "-N",
            action="store_true",
            help="Don't recursively check for child manifests.",
        )

    def __call__(self, args: argparse.Namespace) -> None:
        """Perform the update."""
        manifest, path = dfetch.manifest.manifest.get_manifest()

        exceptions: List[str] = []
        with in_directory(os.path.dirname(path)):
            for project in manifest.projects:
                with catch_runtime_exceptions(exceptions) as exceptions:
                    dfetch.project.make(project).update()

                if not args.non_recursive:
                    exceptions += Update.__update_child_manifests(project, path)

        if exceptions:
            raise RuntimeError("\n".join(exceptions))

    @staticmethod
    def __update_child_manifests(project: ProjectEntry, path: str) -> List[str]:
        exceptions: List[str] = []
        for (
            childmanifest,
            childpath,
        ) in dfetch.manifest.manifest.get_childmanifests(project, skip=[path]):
            with in_directory(os.path.dirname(childpath)):
                for childproject in childmanifest.projects:
                    with catch_runtime_exceptions(exceptions) as exceptions:
                        dfetch.project.make(childproject).update()
        return exceptions
