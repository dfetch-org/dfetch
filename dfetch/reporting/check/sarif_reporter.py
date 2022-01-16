"""*Dfetch* can generate a report in the Sarif format that is by Github from the :ref:`check` results.

Dependending on the state of the projects it will create a report with information.
If all project are up-to-date, nothing will be added to the report.

"""

import json
import re
from typing import Tuple

import attr

from sarif_om import (
    ArtifactLocation,
    Location,
    Message,
    PhysicalLocation,
    Region,
    Result,
    Run,
    SarifLog,
    Tool,
    ToolComponent,
)

from dfetch.log import get_logger
from dfetch.manifest.project import ProjectEntry
from dfetch.manifest.version import Version
from dfetch.reporting.check.reporter import CheckReporter

logger = get_logger(__name__)


class SarifReporter(CheckReporter):
    """Reporter for generating report in sarif format."""

    name = "sarif"

    VERSION = "2.1.0"
    SCHEMA = "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json"

    def __init__(self, manifest_path: str, report_path: str) -> None:
        """Create the sarif reporter.

        Args:
            manifest_path (str): Path to the manifest.
            report_path (str): Output path of the report.
        """
        super().__init__()

        self._manifest_path = manifest_path
        self._report_path = report_path

        self._run = Run(
            tool=Tool(
                driver=ToolComponent(
                    name="DFetch",
                    information_uri="https://dfetch.rtfd.io",
                    rules=[
                        {
                            "id": "unfetched-project",
                            "shortDescription": {"text": "Project was never fetched"},
                        },
                        {
                            "id": "up-to-date-project",
                            "shortDescription": {"text": "Project is up-to-date"},
                        },
                        {
                            "id": "pinned-but-out-of-date-project",
                            "shortDescription": {"text": "Project is out-of-date"},
                        },
                        {
                            "id": "out-of-date-project",
                            "shortDescription": {"text": "Project is out-of-date"},
                        },
                    ],
                )
            )
        )
        self._run.artifacts = [Location()]
        self._run.artifacts[-1].physical_location = manifest_path
        self._run.results = []

    def unfetched_project(
        self, project: ProjectEntry, wanted_version: Version, latest: Version
    ) -> None:
        """Report an unfetched project.

        Args:
            project (ProjectEntry): The unfetched project.
            wanted_version (Version): The wanted version.
            latest (Version): The latest available version.
        """
        msg = f"{project.name} was never fetched!"
        description = (
            f"The manifest requires version '{str(wanted_version) or 'latest'}' of {project.name}. "
            f"it was never fetched, fetch it with 'dfetch update {project.name}. "
            f"The latest version available is '{latest}'"
        )
        self._add_issue(project, "High", "unfetched-project", msg, description)

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
        msg = (
            f"{project.name} wanted & current version is '{str(wanted_version) or 'latest'}',"
            f" but '{latest}' is available."
        )
        description = (
            f"The manifest requires version '{str(wanted_version) or 'latest'}' of {project.name}. "
            f"This is also the current version. There is a newer version available '{latest}'"
            f"You can update the version in the manifest and run 'dfetch update {project.name}'"
        )
        self._add_issue(
            project, "Low", "pinned-but-out-of-date-project", msg, description
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
        msg = f"{project.name} wanted version is '{str(wanted_version) or 'latest'}', but '{latest}' is available."
        description = (
            f"The manifest requires version '{str(wanted_version) or 'latest'}' of {project.name}. "
            f"Currently version '{current}' is present. "
            f"There is a newer version available '{latest}'. "
            f"Please update using 'dfetch update {project.name}."
        )
        self._add_issue(project, "Normal", "out-of-date-project", msg, description)

    def _add_issue(
        self,
        project: ProjectEntry,
        severity: str,
        rule_id: str,
        message: str,
        description: str,
    ) -> None:
        """Add an issue to the report.

        Args:
            project (ProjectEntry): Project with the issue
            severity (str): Level of the issue
            message (str): Message
            description (str): Extended description
        """
        line, col_start, col_end = self._find_name_in_manifest(project.name)

        result = Result(
            message=Message(text=f"{project.name} : {message}"),
            level=severity,
            rule_id=rule_id,
            locations=[
                Location(
                    physical_location=PhysicalLocation(
                        artifact_location=ArtifactLocation(
                            uri=self._manifest_path, index=0
                        ),
                        region=Region(
                            start_line=line,
                            start_column=col_start,
                            end_line=line,
                            end_column=col_end,
                            byte_offset=None,
                            char_offset=None
                        ),
                    )
                )
            ],
        )

        self._run.results += [result]

    def _find_name_in_manifest(self, name: str) -> Tuple[int, int, int]:
        """Find the location of a project name in the manifest."""
        with open(self._manifest_path, "r", encoding="utf-8") as manifest:
            for line_nr, line in enumerate(manifest, start=1):
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

    def dump_to_file(self) -> None:
        """Dump report."""
        log = SarifLog(runs=[self._run], version=self.VERSION, schema_uri=self.SCHEMA)
        with open(self._report_path, "w", encoding="utf-8") as report:
            json.dump(_walk_sarif(attr.asdict(log)), report, indent=4)


def _walk_sarif(sarif_node):
    """Recursively walk through sarif to create readable dictionary."""
    if isinstance(sarif_node, (int, str)):
        return sarif_node
    if isinstance(sarif_node, dict):
        return {
            key: _walk_sarif(value)
            for key, value in sarif_node.items()
            if value is not None
        }
    if isinstance(sarif_node, list):
        return [_walk_sarif(item) for item in sarif_node]
