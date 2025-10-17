"""*Dfetch* can generate multiple reports.

There are several report types that *DFetch* can generate.
"""

import argparse
import glob
import os

import dfetch.commands.command
import dfetch.manifest.manifest
import dfetch.util.util
from dfetch.log import get_logger
from dfetch.manifest.project import ProjectEntry
from dfetch.project.metadata import Metadata
from dfetch.project.vcs import VCS
from dfetch.reporting import REPORTERS, ReportTypes
from dfetch.util.license import License, guess_license_in_file

logger = get_logger(__name__)

# Only accept license guesses with below or higher confidence to avoid false positives
LICENSE_PROBABILITY_THRESHOLD = 0.80


class Report(dfetch.commands.command.Command):
    """Generate reports containing information about the projects components.

    Report can be stdout, sbom
    """

    @staticmethod
    def create_menu(subparsers: dfetch.commands.command.SubparserActionType) -> None:
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
            "-t",
            "--type",
            type=ReportTypes,
            choices=list(ReportTypes),
            default=ReportTypes.STDOUT,
            help="Type of report to generate.",
        )

    def __call__(self, args: argparse.Namespace) -> None:
        """Generate the report."""
        manifest = dfetch.manifest.manifest.get_manifest()

        with dfetch.util.util.in_directory(os.path.dirname(manifest.path)):
            reporter = REPORTERS[args.type](manifest)

            for project in manifest.selected_projects(args.projects):
                determined_licenses = self._determine_licenses(project)
                version = self._determine_version(project)
                reporter.add_project(
                    project=project, licenses=determined_licenses, version=version
                )

            if reporter.dump_to_file(args.outfile):
                logger.info(f"Generated {reporter.name} report: {args.outfile}")

    @staticmethod
    def _determine_licenses(project: ProjectEntry) -> list[License]:
        """Try to determine license of fetched project."""
        if not os.path.exists(project.destination):
            logger.print_warning_line(
                project.name, "Never fetched, fetch it to get license info."
            )
            return []

        license_files = []
        with dfetch.util.util.in_directory(project.destination):

            for license_file in filter(VCS.is_license_file, glob.glob("*")):
                logger.debug(f"Found license file {license_file} for {project.name}")
                guessed_license = guess_license_in_file(license_file)

                if (
                    guessed_license
                    and guessed_license.probability > LICENSE_PROBABILITY_THRESHOLD
                ):
                    license_files.append(guessed_license)
                else:
                    logger.print_warning_line(
                        project.name, f"Could not determine license in {license_file}"
                    )
        return license_files

    @staticmethod
    def _determine_version(project: ProjectEntry) -> str:
        """Determine the fetched version."""
        try:
            metadata = Metadata.from_file(Metadata.from_project_entry(project).path)
            version = metadata.tag or metadata.revision or ""
        except FileNotFoundError:
            version = project.tag or project.revision or ""
        return version
