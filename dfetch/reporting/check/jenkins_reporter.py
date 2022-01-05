"""*Dfetch* can generate an report on stdout.

Dependending on the state of the projects it will show as much information
from the manifest or the metadata (``.dfetch_data.yaml``).

Add to pipeline using warnings-ng plugin:

recordIssues tool: issues(pattern: 'jenkins.json', name: 'DFetch')
"""

import os
import re
import json
from typing import Dict, Tuple, Any

from dfetch.log import get_logger
from dfetch.manifest.project import ProjectEntry
from dfetch.manifest.manifest import Manifest
from dfetch.manifest.version import Version
from dfetch.reporting.check.reporter import CheckReporter

logger = get_logger(__name__)


class JenkinsReporter(CheckReporter):
    """Reporter for generating report on stdout."""

    name = "jenkins"

    def __init__(self, manifest_path: str, report_path: str) -> None:
        super().__init__()

        self._manifest_path = manifest_path
        self._report_path = report_path

        self._report: Dict[str, Any] = {
            "_class": "io.jenkins.plugins.analysis.core.restapi.ReportApi",
            "issues": [],
        }

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
        self._add_issue(project, "High", msg, description)

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
            project (ProjectEntry): [description]
            wanted_version (Version): [description]
            latest (Version): [description]
        """
        msg = f"{project.name} wanted & current version is '{str(wanted_version) or 'latest'}', but '{latest}' is available."
        description = (
            f"The manifest requires version '{str(wanted_version) or 'latest'}' of {project.name}. "
            f"This is also the current version. There is a newer version available '{latest}'"
            f"You can update the version in the manifest and run 'dfetch update {project.name}'"
        )
        self._add_issue(project, "Low", msg, description)

    def out_of_date_project(
        self, project: ProjectEntry, wanted_version: Version, current: Version, latest: Version
    ) -> None:
        """Report an out-of-date project.

        Args:
            project (ProjectEntry): [description]
            wanted_version (Version): [description]
            latest (Version): [description]
        """
        msg = f"{project.name} wanted version is '{str(wanted_version) or 'latest'}', but '{latest}' is available."
        description = (
            f"The manifest requires version '{str(wanted_version) or 'latest'}' of {project.name}. "
            f"Currently version '{current}' is present. "
            f"There is a newer version available '{latest}'. "
            f"Please update using 'dfetch update {project.name}."
        )
        self._add_issue(project, "Normal", msg, description)

    def _add_issue(
        self, project: ProjectEntry, severity: str, message: str, description: str
    ) -> None:
        """Add an issue to the report.

        Args:
            project (ProjectEntry): Project with the issue
            severity (str): Level of the issue
            message (str): Message
            description (str): Extended description
        """
        line, col_start, col_end = self._find_name_in_manifest(project.name)
        self._report["issues"] += [
            {
                "fileName": os.path.relpath(self._manifest_path),
                "severity": severity,
                "message": f"{project.name} : {message}",
                "description": description,
                "lineStart": line,
                "lineEnd": line,
                "columnStart": col_start,
                "columnEnd": col_end,
            }
        ]

    def _find_name_in_manifest(self, name: str) -> Tuple[int, int, int]:
        """Find the location of a project na e in the manifest."""
        with open(self._manifest_path, "r") as manifest:
            for nr, line in enumerate(manifest, start=1):
                match = re.search(rf"^\s+-\s*name:\s*(?P<name>{name})\s", line)

                if match:
                    return (nr, int(match.start("name")) + 1, int(match.end("name")))
        raise RuntimeError("Water is burning")

    def dump_to_file(self) -> None:
        """Dump report."""
        with open(self._report_path, "w") as report:
            json.dump(self._report, report, indent=4)
