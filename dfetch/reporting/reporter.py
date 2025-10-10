"""Abstract reporting interface."""

from abc import ABC, abstractmethod
from typing import List

from dfetch.manifest.manifest import Manifest
from dfetch.manifest.project import ProjectEntry
from dfetch.util.license import License


class Reporter(ABC):
    """Reporter for generating report."""

    name: str = "abstract"

    @abstractmethod
    def __init__(self, manifest: Manifest) -> None:
        """Create the reporter.

        Args:
            manifest (Manifest): The manifest to report on
        """

    @abstractmethod
    def add_project(
        self,
        project: ProjectEntry,
        licenses: List[License],
        version: str,
    ) -> None:
        """Add a project to the report."""

    @abstractmethod
    def dump_to_file(self, outfile: str) -> bool:
        """Do nothing."""
