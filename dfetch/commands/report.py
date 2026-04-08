"""*Dfetch* can generate reports about the projects in your manifest.

Two report types are available via the ``-t`` / ``--type`` flag:

``stdout`` (default)
    Prints a dependency inventory to the terminal. For each project it shows
    the remote URL, branch/tag/revision, last-fetch timestamp, applied patches,
    and any licences detected in the fetched source tree.

``sbom``
    Generates a `CycloneDX 1.6 <https://cyclonedx.org/>`_ Software Bill of
    Materials (SBOM) as a JSON file (``report.json`` by default, override with
    ``-o``). The SBOM includes package URLs (PURLs), VCS references, licence
    evidence, and — for archive projects — an optional SHA-256 integrity hash.

    This can be uploaded to GitHub as a supply-chain asset or attached to a
    GitLab pipeline as a ``cyclonedx`` artefact.

Licence detection
~~~~~~~~~~~~~~~~~
*Dfetch* scans each fetched project for common licence files (``LICENSE``,
``COPYING``, etc.) and uses a best-effort heuristic to identify the licence
type.  Only matches with a confidence of 80 % or higher are used.

In the SBOM report the ``licenses`` field is always populated for fetched
projects:

* **Identified** — the SPDX identifier is recorded.
* **File found, unclassifiable** — ``NOASSERTION`` is set and a
  ``dfetch:license:finding`` property names the problematic file(s).
* **No licence file found** — ``NOASSERTION`` is set and a
  ``dfetch:license:finding`` property states that no file was found.

This guarantees the field is never silently omitted and improves transparency
for downstream compliance analysis.

For every scanned component, the SBOM additionally records
``dfetch:license:<spdx-id>:confidence`` (per identified licence),
``dfetch:license:threshold``, and ``dfetch:license:tool`` so auditors can
reproduce or re-evaluate detection results.
"""

import argparse
import glob
import os

import dfetch.commands.command
import dfetch.manifest.manifest
import dfetch.util.util
from dfetch.log import get_logger
from dfetch.manifest.project import ProjectEntry
from dfetch.project import create_super_project
from dfetch.project.metadata import Metadata
from dfetch.reporting import REPORTERS, ReportTypes
from dfetch.util.license import (
    LicenseScanResult,
    guess_license_in_file,
    is_license_file,
)

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
        superproject = create_super_project()

        with dfetch.util.util.in_directory(superproject.root_directory):
            reporter = REPORTERS[args.type](superproject.manifest)

            for project in superproject.manifest.selected_projects(args.projects):
                license_scan = self._determine_licenses(project)
                version = self._determine_version(project)
                reporter.add_project(
                    project=project, license_scan=license_scan, version=version
                )

            if reporter.dump_to_file(args.outfile):
                logger.info(f"Generated {reporter.name} report: {args.outfile}")

    @staticmethod
    def _determine_licenses(project: ProjectEntry) -> LicenseScanResult:
        """Try to determine license of fetched project."""
        if not os.path.exists(project.destination):
            logger.print_warning_line(
                project.name, "Never fetched, fetch it to get license info."
            )
            return LicenseScanResult(was_scanned=False)

        identified = []
        unclassified = []
        with dfetch.util.util.in_directory(project.destination):
            for license_file in filter(is_license_file, glob.glob("*")):
                logger.debug(f"Found license file {license_file} for {project.name}")
                guessed_license = guess_license_in_file(license_file)

                if (
                    guessed_license
                    and guessed_license.probability > LICENSE_PROBABILITY_THRESHOLD
                ):
                    identified.append(guessed_license)
                else:
                    unclassified.append(license_file)
                    logger.print_warning_line(
                        project.name, f"Could not determine license in {license_file}"
                    )
        return LicenseScanResult(
            identified=identified,
            unclassified_files=unclassified,
            was_scanned=True,
            threshold=LICENSE_PROBABILITY_THRESHOLD,
        )

    @staticmethod
    def _determine_version(project: ProjectEntry) -> str:
        """Determine the fetched version.

        For archive projects the sha256 hash (``sha256:<hex>``) stored in the
        metadata *revision* field is used as the version identifier.  When no
        metadata is present yet, the ``integrity.hash`` field from the manifest
        is used as fallback so the SBOM can still be generated before the first
        fetch.
        """
        try:
            metadata = Metadata.from_file(Metadata.from_project_entry(project).path)
            version = (
                metadata.tag
                or metadata.revision
                or project.tag
                or project.revision
                or project.hash
                or ""
            )
        except FileNotFoundError:
            version = project.tag or project.revision or project.hash or ""
        return version
