"""Abstract reporting interface."""

from abc import ABC, abstractmethod

from dfetch.manifest.manifest import Manifest
from dfetch.manifest.project import ProjectEntry
from dfetch.util.license import License


class Reporter(ABC):
    """Reporter for generating report."""

    name: str = "abstract"

    def __init__(self, manifest: Manifest) -> None:
        """Create the reporter.

        Args:
            manifest (Manifest): The manifest to report on
        """
        self._manifest = manifest

    @property
    def manifest(self) -> Manifest:
        """Get the manifest."""
        return self._manifest

    @abstractmethod
    def add_project(
        self,
        project: ProjectEntry,
        licenses: list[License],
        version: str,
    ) -> None:
        """Add a project to the report."""

    @abstractmethod
    def dump_to_file(self, outfile: str) -> bool:
        """Do nothing."""
