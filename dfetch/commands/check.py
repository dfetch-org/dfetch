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

"""

import argparse
import os
from typing import Any, List  # pylint: disable=unused-import

import dfetch.commands.command
import dfetch.manifest.manifest
import dfetch.manifest.validate
import dfetch.project
from dfetch.commands.common import check_child_manifests
from dfetch.log import get_logger
from dfetch.reporting.check.code_climate_reporter import CodeClimateReporter
from dfetch.reporting.check.jenkins_reporter import JenkinsReporter
from dfetch.reporting.check.reporter import CheckReporter
from dfetch.reporting.check.sarif_reporter import SarifReporter
from dfetch.reporting.check.stdout_reporter import CheckStdoutReporter
from dfetch.util.util import catch_runtime_exceptions, in_directory

logger = get_logger(__name__)


class Check(dfetch.commands.command.Command):
    """Check all projects for updates.

    Check all project to see if there are any new updates.
    """

    @staticmethod
    def create_menu(subparsers: "argparse._SubParsersAction[Any]") -> None:
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
        parser.add_argument(
            "--jenkins-json",
            metavar="outfile",
            type=str,
            help="Generate a JSON that can be parsed by Jenkins.",
        )
        parser.add_argument(
            "--sarif",
            metavar="outfile",
            type=str,
            help="Generate a Sarif JSON that can be parsed by Github.",
        )
        parser.add_argument(
            "--code-climate",
            metavar="outfile",
            type=str,
            help="Generate a code-climate JSON that can be parsed by Gitlab.",
        )

    def __call__(self, args: argparse.Namespace) -> None:
        """Perform the check."""
        manifest, path = dfetch.manifest.manifest.get_manifest()
        reporters = self._get_reporters(args, path)

        with in_directory(os.path.dirname(path)):
            exceptions: List[str] = []
            for project in manifest.selected_projects(args.projects):
                with catch_runtime_exceptions(exceptions) as exceptions:
                    dfetch.project.make(project).check_for_update(reporters)

                if not args.no_recommendations and os.path.isdir(project.destination):
                    with in_directory(project.destination):
                        check_child_manifests(manifest, project, path)

            for reporter in reporters:
                reporter.dump_to_file()

        if exceptions:
            raise RuntimeError("\n".join(exceptions))

    @staticmethod
    def _get_reporters(args: argparse.Namespace, path: str) -> List[CheckReporter]:
        """Get all reporters.

        Args:
            args (argparse.Namespace): Arguments given to the command line
            path (str): Path to the manifest

        Returns:
            List[CheckReporter]: List of reporters that each provide a unique report
        """
        reporters: List[CheckReporter] = [CheckStdoutReporter(path)]
        if args.jenkins_json:
            reporters += [JenkinsReporter(path, args.jenkins_json)]
        if args.sarif:
            reporters += [SarifReporter(path, args.sarif)]
        if args.code_climate:
            reporters += [CodeClimateReporter(path, args.code_climate)]
        return reporters
