"""Interface for reporting check results."""
from abc import ABC, abstractmethod

from dfetch.manifest.project import ProjectEntry
from dfetch.manifest.version import Version


class AbstractCheckReporter(ABC):
    """Reporter for generating report."""

    @abstractmethod
    def __init__(self, manifest_path: str) -> None:
        """Create the reporter.

        Args:
            manifest_path (str): The path to the manifest.
        """

    @abstractmethod
    def unfetched_project(
        self, project: ProjectEntry, wanted_version: Version, latest: Version
    ) -> None:
        """Report an unfetched project.

        Args:
            project (ProjectEntry): The unfetched project.
            wanted_version (Version): The wanted version.
            latest (Version): The latest available version.
        """

    @abstractmethod
    def up_to_date_project(self, project: ProjectEntry, latest: Version) -> None:
        """Report an up-to-date project.

        Args:
            project (ProjectEntry): The up-to-date project
            latest (Version): The last version.
        """

    @abstractmethod
    def pinned_but_out_of_date_project(
        self, project: ProjectEntry, wanted_version: Version, latest: Version
    ) -> None:
        """Report an pinned but out-of-date project.

        Args:
            project (ProjectEntry): Project that is pinned but out-of-date
            wanted_version (Version): Version that is wanted by manifest
            latest (Version): Available version
        """

    @abstractmethod
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

    @abstractmethod
    def local_changes(self, project: ProjectEntry) -> None:
        """Report an project with local changes.

        Args:
            project (ProjectEntry): The project with local changes.
        """

    @abstractmethod
    def dump_to_file(self) -> None:
        """Do nothing."""
