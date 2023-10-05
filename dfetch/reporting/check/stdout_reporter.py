"""*Dfetch* can generate an report on stdout.

Depending on the state of the projects it will show as much information
from the manifest or the metadata (``.dfetch_data.yaml``).

Add to pipeline using warnings-ng plugin:

recordIssues tool: issues(pattern: 'jenkins.json', name: 'DFetch')
"""

from dfetch.log import get_logger
from dfetch.manifest.project import ProjectEntry
from dfetch.manifest.version import Version
from dfetch.reporting.check.reporter import CheckReporter, Issue

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
            project (ProjectEntry): Project that is pinned but out-of-date
            wanted_version (Version): Version that is wanted by manifest
            latest (Version): Available version
        """
        logger.print_info_line(
            project.name, f"wanted & current ({wanted_version}), available ({latest})"
        )

    def out_of_date_project(
        self,
        project: ProjectEntry,
        wanted_version: Version,
        current: Version,
        latest: Version,
    ) -> None:
        """Report an out-of-date project.

        Args:
            project (ProjectEntry): Project that is out-of-date
            wanted_version (Version): Version that is wanted by manifest
            current (Version): Current version on disk
            latest (Version): Available version
        """
        logger.print_info_line(
            project.name,
            f"wanted ({str(wanted_version) or 'latest'}), "
            f"current ({current}), available ({latest})",
        )

    def local_changes(self, project: ProjectEntry) -> None:
        """Report an project with local changes.

        Args:
            project (ProjectEntry): The project with local changes.
        """
        logger.print_warning_line(
            project.name,
            "Local changes were detected, "
            f"please generate a patch using 'dfetch diff {project.name}' and add it "
            "to your manifest using 'patch:'. Alternatively overwrite the local changes "
            f"with 'dfetch update --force {project.name}'",
        )

    def add_issue(self, project: ProjectEntry, issue: Issue) -> None:
        """Add an issue to the report.

        Args:
            project (ProjectEntry): Project with the issue
            issue (Issue): The issue to add
        """
        del project
        del issue

    def dump_to_file(self) -> None:
        """Dump report."""
