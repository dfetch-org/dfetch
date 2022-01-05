"""Abstract reporting interface."""

from abc import ABC, abstractmethod

from dfetch.manifest.project import ProjectEntry, Version


class CheckReporter(ABC):
    """Reporter for generating report."""

    name: str = "abstract"

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
            project (ProjectEntry): [description]
            wanted_version (Version): [description]
            latest (Version): [description]
        """

    @abstractmethod
    def out_of_date_project(
        self, project: ProjectEntry, wanted_version: Version, current: Version, latest: Version
    ) -> None:
        """Report an out-of-date project.

        Args:
            project (ProjectEntry): [description]
            wanted_version (Version): [description]
            current (Version): [description]
            latest (Version): [description]
        """

    @abstractmethod
    def dump_to_file(self, outfile: str) -> bool:
        """Do nothing."""
