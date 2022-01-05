"""*Dfetch* can generate an report on stdout.

Dependending on the state of the projects it will show as much information
from the manifest or the metadata (``.dfetch_data.yaml``).

Add to pipeline using warnings-ng plugin:

recordIssues tool: issues(pattern: 'jenkins.json', name: 'DFetch')
"""

import json

from dfetch.log import get_logger
from dfetch.manifest.project import ProjectEntry
from dfetch.manifest.version import Version
from dfetch.reporting.check.reporter import CheckReporter

logger = get_logger(__name__)


class CheckStdoutReporter(CheckReporter):
    """Reporter for generating report on stdout."""

    name = "stdout"

    def unfetched_project(
        self, project: ProjectEntry, wanted_version: Version, latest: Version
    ) -> None:
        """Report an unfetched project.

        Args:
            project (ProjectEntry): The unfetched project.
            wanted_version (Version): The wanted version.
            latest (Version): The latest available version.
        """
        wanted = f"wanted ({wanted_version}), " if any(wanted_version) else ""
        logger.print_info_line(project.name, f"{wanted}available ({latest})")

    def up_to_date_project(self, project: ProjectEntry, latest: Version) -> None:
        """Report an up-to-date project.

        Args:
            project (ProjectEntry): The up-to-date project
            latest (Version): The last version.
        """
        logger.print_info_line(project.name, f"up-to-date ({latest})")

    def pinned_but_out_of_date_project(
        self, project: ProjectEntry, wanted_version: Version, latest: Version
    ) -> None:
        """Report an pinned but out-of-date project.

        Args:
            project (ProjectEntry): [description]
            wanted_version (Version): [description]
            latest (Version): [description]
        """
        logger.print_info_line(
            project.name, f"wanted & current ({wanted_version}), available ({latest})"
        )

    def out_of_date_project(
        self, project: ProjectEntry, wanted_version: Version, current: Version,  latest: Version
    ) -> None:
        """Report an out-of-date project.

        Args:
            project (ProjectEntry): [description]
            wanted_version (Version): [description]
            latest (Version): [description]
        """
        logger.print_info_line(
            project.name,
            f"wanted ({str(wanted_version) or 'latest'}), "
            f"current ({current}), available ({latest})",
        )

    def _log_project(self, msg: str) -> None:
        logger.print_info_line(self.__project.name, msg)

    def dump_to_file(self) -> None:
        """Dump report."""
        pass
