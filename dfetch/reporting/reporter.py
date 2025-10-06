"""Abstract reporting interface."""

import io
import re
from abc import ABC, abstractmethod
from typing import List, Tuple

from dfetch.manifest.project import ProjectEntry
from dfetch.util.license import License


class Reporter(ABC):
    """Reporter for generating report."""

    name: str = "abstract"

    def __init__(self, manifest_path: str) -> None:
        """Create the reporter.

        Args:
            manifest_path (str): The path to the manifest.
        """
        self._manifest_path = manifest_path
        with open(self._manifest_path, "r", encoding="utf-8") as manifest:
            self._manifest_buffer = io.StringIO(manifest.read())

    @abstractmethod
    def add_project(
        self,
        project: ProjectEntry,
        licenses: List[License],
        version: str,
    ) -> None:
        """Add a project to the report."""

    def find_name_in_manifest(self, name: str) -> Tuple[int, int, int]:
        """Find the location of a project name in the manifest."""
        self._manifest_buffer.seek(0)
        for line_nr, line in enumerate(self._manifest_buffer, start=1):
            match = re.search(rf"^\s+-\s*name:\s*(?P<name>{name})\s", line)

            if match:
                return (
                    line_nr,
                    int(match.start("name")) + 1,
                    int(match.end("name")),
                )
        raise RuntimeError(
            "An entry from the manifest was provided,"
            " that doesn't exist in the manifest!"
        )

    @abstractmethod
    def dump_to_file(self, outfile: str) -> bool:
        """Do nothing."""
