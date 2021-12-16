"""To check if your projects are up-to-date, you can let dfetch check it.

For each project the local version (based on tag or revision) will be compared against
the available version. If there are new versions available this will be shown.

.. uml:: /static/uml/check.puml

Child-manifests
~~~~~~~~~~~~~~~

It is possible that fetched projects have manifests of their own.
After these projects are fetched (with ``dfetch update``), the manifests are read as well
and will be checked to look for further dependencies. If you don't what recommendations, you can prevent *Dfetch*
checking child-manifests with ``--no-recommendations``.

.. note:: Any name or destination clashes are currently up to the user.

"""

import argparse
import os
from typing import List

import yaml

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

                if not args.no_recommendations and os.path.isdir(project.destination):
                    with in_directory(project.destination):
                        exceptions += Check._check_child_manifests(
                            manifest, project, path
                        )

        if exceptions:
            raise RuntimeError("\n".join(exceptions))

    @staticmethod
    def _check_child_manifests(
        manifest: dfetch.manifest.manifest.Manifest, project: ProjectEntry, path: str
    ) -> List[str]:
        exceptions: List[str] = []

        recommendations: List[ProjectEntry] = []
        for childmanifest in dfetch.manifest.manifest.get_childmanifests(skip=[path]):
            for childproject in childmanifest.projects:

                if childproject.remote_url not in [
                    project.remote_url for project in manifest.projects
                ]:
                    recommendations.append(childproject.as_recommendation())

        if recommendations:
            logger.warning(
                f"\n{project.name} depends on the following project(s) which are not part of your manifest:",
            )

            recommendation_json = yaml.dump(
                [proj.as_yaml() for proj in recommendations], indent=4, sort_keys=False
            )
            logger.warning("")
            for line in recommendation_json.splitlines():
                logger.warning(line)

        return exceptions
