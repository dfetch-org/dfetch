"""*Dfetch* can generate multiple reports."""

import argparse
import glob
import itertools
import os

import infer_license

import dfetch.commands.command
import dfetch.manifest.manifest
import dfetch.util.util
from dfetch.log import get_logger
from dfetch.manifest.project import ProjectEntry
from dfetch.project.metadata import Metadata
from dfetch.reporting import Reporter
from dfetch.reporting.sbom_reporter import SbomReporter
from dfetch.reporting.stdout_reporter import StdoutReporter

logger = get_logger(__name__)


class Report(dfetch.commands.command.Command):
    """Generate reports containing information about the projects components.

    Generate a file for tracking licenses and vulnerabilities.
    """

    @staticmethod
    def create_menu(subparsers: "argparse._SubParsersAction") -> None:
        """Add the parser menu for this action."""
        parser = dfetch.commands.command.Command.parser(subparsers, Report)

        parser.add_argument(
            "-o",
            "--outfile",
            metavar="<filename>",
            type=str,
            default="report.json",
            help="Report filename",
        )

        parser.add_argument(
            "projects",
            metavar="<project>",
            type=str,
            nargs="*",
            help="Specific project(s) to report",
        )

        parser.add_argument(
            "-s",
            "--sbom",
            action="store_true",
            default=False,
            help="Generate an software BoM.",
        )

    def __call__(self, args: argparse.Namespace) -> None:
        """Generate the report."""
        manifest, path = dfetch.manifest.manifest.get_manifest()

        reporter: Reporter = SbomReporter() if args.sbom else StdoutReporter()

        with dfetch.util.util.in_directory(os.path.dirname(path)):
            for project in manifest.selected_projects(args.projects):
                determined_license = self._determine_license(project)
                version = self._determine_version(project)
                reporter.add_project(project, determined_license, version)

            if reporter.dump_to_file(args.outfile):
                logger.info(f"Generated {reporter.name} report: {args.outfile}")

    @staticmethod
    def _determine_license(project: ProjectEntry) -> str:
        """Try to determine license of fetched project."""
        if not os.path.exists(project.destination):
            logger.print_warning_line(
                project.name, "Never fetched, fetch it to get license info."
            )
            return ""

        with dfetch.util.util.in_directory(project.destination):
            for license_file in itertools.chain(
                glob.glob("LICENSE*"), glob.glob("COPYING*")
            ):
                logger.debug(f"Found license file {license_file} for {project.name}")
                guessed_license = infer_license.api.guess_file(license_file)

                if guessed_license:
                    return str(guessed_license.name)

                logger.print_warning_line(
                    project.name, f"Could not determine license in {license_file}"
                )

        return ""

    @staticmethod
    def _determine_version(project: ProjectEntry) -> str:
        """Determine the fetched version."""
        try:
            metadata = Metadata.from_file(Metadata.from_project_entry(project).path)
            version = metadata.tag or metadata.revision or ""
        except FileNotFoundError:
            version = project.tag or project.revision or ""
        return version
