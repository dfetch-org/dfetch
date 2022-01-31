"""Abstract reporting interface."""

import io
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Sequence, Tuple

from dfetch.manifest.project import ProjectEntry
from dfetch.manifest.version import Version


class IssueSeverity(Enum):
    """Issue severity."""

    HIGH = "High"
    NORMAL = "Normal"
    LOW = "Low"


@dataclass
class Issue:
    """A found issue."""

    severity: IssueSeverity
    rule_id: str
    message: str
    description: str


@dataclass
class Rule:
    """Rule for dependencies."""

    name: str
    description: str


class CheckReporter(ABC):
    """Reporter for generating report."""

    name: str = "abstract"

    rules: Sequence[Rule] = [
        Rule(name="unfetched-project", description="Project was never fetched"),
        Rule(name="up-to-date-project", description="Project is up-to-date"),
        Rule(
            name="pinned-but-out-of-date-project",
            description="Project is pinned, but out-of-date",
        ),
        Rule(name="out-of-date-project", description="Project is out-of-date"),
    ]

    def __init__(self, manifest_path: str) -> None:
        """Create the reporter.

        Args:
            manifest_path (str): The path to the manifest.
        """
        self._manifest_path = manifest_path
        with open(self._manifest_path, "r", encoding="utf-8") as manifest:
            self._manifest_buffer = io.StringIO(manifest.read())

    def unfetched_project(
        self, project: ProjectEntry, wanted_version: Version, latest: Version
    ) -> None:
        """Report an unfetched project.

        Args:
            project (ProjectEntry): The unfetched project.
            wanted_version (Version): The wanted version.
            latest (Version): The latest available version.
        """
        issue = Issue(
            severity=IssueSeverity.HIGH,
            rule_id="unfetched-project",
            message=f"{project.name} was never fetched!",
            description=(
                f"The manifest requires version '{str(wanted_version) or 'latest'}' of {project.name}. "
                f"it was never fetched, fetch it with 'dfetch update {project.name}. "
                f"The latest version available is '{latest}'"
            ),
        )
        self.add_issue(project, issue)

    def up_to_date_project(  # pylint: disable=no-self-use
        self, project: ProjectEntry, latest: Version
    ) -> None:
        """Report an up-to-date project.

        Args:
            project (ProjectEntry): The up-to-date project
            latest (Version): The last version.
        """
        del project
        del latest

    def pinned_but_out_of_date_project(
        self, project: ProjectEntry, wanted_version: Version, latest: Version
    ) -> None:
        """Report an pinned but out-of-date project.

        Args:
            project (ProjectEntry): Project that is pinned but out-of-date
            wanted_version (Version): Version that is wanted by manifest
            latest (Version): Available version
        """
        issue = Issue(
            severity=IssueSeverity.LOW,
            rule_id="pinned-but-out-of-date-project",
            message=(
                f"{project.name} wanted & current version is '{str(wanted_version) or 'latest'}',"
                f" but '{latest}' is available."
            ),
            description=(
                f"The manifest requires version '{str(wanted_version) or 'latest'}' of {project.name}. "
                f"This is also the current version. There is a newer version available '{latest}'"
                f"You can update the version in the manifest and run 'dfetch update {project.name}'"
            ),
        )
        self.add_issue(project, issue)

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
        issue = Issue(
            severity=IssueSeverity.NORMAL,
            rule_id="out-of-date-project",
            message=f"{project.name} current version is '{current}',"
            f" the wanted version is '{str(wanted_version) or 'latest'}',"
            f" but '{latest}' is available.",
            description=(
                f"The manifest requires version '{str(wanted_version) or 'latest'}' of {project.name}. "
                f"Currently version '{current}' is present. "
                f"There is a newer version available '{latest}'. "
                f"Please update using 'dfetch update {project.name}."
            ),
        )
        self.add_issue(project, issue)

    @abstractmethod
    def add_issue(self, project: ProjectEntry, issue: Issue) -> None:
        """Add an issue to the report.

        Args:
            project (ProjectEntry): Project with the issue
            issue (Issue): The issue to add
        """

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
    def dump_to_file(self) -> None:
        """Do nothing."""
