"""Abstract reporting interface."""

from abc import ABC, abstractmethod

from dfetch.manifest.project import ProjectEntry


class Reporter(ABC):
    """Reporter for generating report."""

    name: str = "abstract"

    @abstractmethod
    def add_project(
        self, project: ProjectEntry, license_name: str, version: str
    ) -> None:
        """Add a project to the report."""

    @abstractmethod
    def dump_to_file(self, outfile: str) -> bool:
        """Do nothing."""
