"""Report issues found during check.

*DFetch* can report its results of checking in a form that is usable for several other tools.
See the respective sections for details about using and configuring those reporters.

All reports can contain the following results:

* ``unfetched-project``
    Project was never fetched. Fetch it using :ref:`dfetch update <update>`.
* ``up-to-date-project``
    Project is up-to-date.
* ``pinned-but-out-of-date-project``
    Project is pinned, but out-of-date. Either ignore this message, or update the version in the manifest.
* ``out-of-date-project``
    Project is out-of-date. Update the project using :ref:`dfetch update <update>`.
* ``local-changes-in-project``
    Project was locally changed. Create a patch file using :ref:`dfetch diff <diff>` and add it to your manifest
    using the :ref:`patch <patch>` attribute.


.. note:: When a ``dfetch check`` is performed on a different platform than the original
          ``dfetch update`` the line-endings might result in a false positive of ``local-changes-in-project``.

"""

import io
import re
from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Sequence, Tuple

from dfetch.manifest.project import ProjectEntry
from dfetch.manifest.version import Version
from dfetch.project.abstract_check_reporter import AbstractCheckReporter


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
    long_description: str


class CheckReporter(AbstractCheckReporter):
    """Reporter for generating report."""

    name: str = "abstract"

    rules: Sequence[Rule] = [
        Rule(
            name="unfetched-project",
            description="Project was never fetched",
            long_description=(
                "The project mentioned in the manifest was never fetched, fetch it with 'dfetch update <project>'. "
                "After fetching, commit the updated project to your repository."
            ),
        ),
        Rule(
            name="up-to-date-project",
            description="Project is up-to-date",
            long_description=(
                "The project mentioned in the manifest is up-to-date, everything is ok, nothing to do."
            ),
        ),
        Rule(
            name="pinned-but-out-of-date-project",
            description="Project is pinned, but out-of-date",
            long_description=(
                "The project mentioned in the manifest is pinned to a specific version, "
                "For instance a branch, tag, or revision. This is currently the state of the project. "
                "However a newer version is available at the upstream of the project. "
                "Either ignore this warning or update the version to the latest and update using "
                "'dfetch update <project>' and commit the result to your repository."
            ),
        ),
        Rule(
            name="out-of-date-project",
            description="Project is out-of-date",
            long_description=(
                "The project is configured to always follow the latest version, "
                "There is a newer version available at the upstream of the project. "
                "Please update the project using 'dfetch update <project>' "
                "and commit the result to your repository."
            ),
        ),
        Rule(
            name="local-changes-in-project",
            description="Project was locally changed",
            long_description=(
                "The files of this project are different then when they were added, "
                "Please create a patch using 'dfetch diff <project>' and add it to the "
                "manifest using the 'patch:' attribute. Or better yet, upstream the changes "
                "and update your project. "
                "When running 'dfetch check' on a platform with different line endings, then this "
                "warning is likely a false positive."
            ),
        ),
    ]

    def __init__(self, manifest_path: str) -> None:
        """Create the reporter.

        Args:
            manifest_path (str): The path to the manifest.
        """
        super().__init__(manifest_path=manifest_path)
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

    def up_to_date_project(self, project: ProjectEntry, latest: Version) -> None:
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
                f"This is also the current version. There is a newer version available '{latest}' "
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

    def local_changes(self, project: ProjectEntry) -> None:
        """Report an project with local changes.

        Args:
            project (ProjectEntry): The project with local changes.
        """
        issue = Issue(
            severity=IssueSeverity.NORMAL,
            rule_id="local-changes-in-project",
            message=f"{project.name} has local changes, please create a patch file or upstream the changes.",
            description=(
                f"{project.name} has local changes, please create a patch file"
                f" using 'dfetch diff {project.name}. This patch file can either be"
                " used to directly from the manifest using the patch attribute, or upstreamed."
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
