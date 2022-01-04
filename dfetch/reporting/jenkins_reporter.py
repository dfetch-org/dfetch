"""*Dfetch* can generate an report on stdout.

Dependending on the state of the projects it will show as much information
from the manifest or the metadata (``.dfetch_data.yaml``).

Add to pipeline using warnings-ng plugin:

recordIssues tool: issues(pattern: 'jenkins.json', name: 'DFetch')
"""

import os
import re
import json
from typing import  Dict, Tuple, Any

from dfetch.log import get_logger
from dfetch.manifest.project import ProjectEntry
from dfetch.manifest.manifest import Manifest
from dfetch.reporting.reporter import CheckReporter

logger = get_logger(__name__)


class JenkinsReporter:
    """Reporter for generating report on stdout."""

    name = "jenkins"

    def __init__(self, manifest: Manifest, path: str) -> None:
        super().__init__()

        self._manifest_path = path

        self._report: Dict[str, Any] = {
            "_class": "io.jenkins.plugins.analysis.core.restapi.ReportApi",
            "issues": [],
        }

    def add_project_warning(self, project: ProjectEntry, message: str) -> None:
        """Add a project to the report."""
        line, col_start, col_end = self._find_line_in_manifest(project.name)
        self._report['issues'] += [
            {
                "fileName": os.path.relpath(self._manifest_path),
                "severity": "Normal",
                "message": f"{project.name} : {message}",
                "lineStart": line,
                "lineEnd": line,
                "columnStart": col_start,
                "columnEnd": col_end,
                "packageName": project.name,
                "origin": project.remote_url,
                "reference": project.version,
            }
        ]

    def add_project_note(self, project: ProjectEntry, message: str) -> None:
        """Add a project to the report."""

        line, col_start, col_end = self._find_line_in_manifest(project.name)
        self._report['issues'] += [
            {
                "fileName": os.path.relpath(self._manifest_path),
                "severity": "Low",
                "message": f"{project.name} : {message}",
                "lineStart": line,
                "lineEnd": line,
                "columnStart": col_start,
                "columnEnd": col_end,
                "packageName": project.name,
                "origin": project.remote_url,
                "reference": project.version,
            }
        ]

    def _find_line_in_manifest(self, name: str) -> Tuple[int, int, int]:

        with open(self._manifest_path, "r") as manifest:
            for nr, line in enumerate(manifest, start=1):
                match = re.search(rf"^\s+-\s*name:\s*(?P<name>{name})\s", line)

                if match:
                    return (nr, int(match.start("name")), int(match.end("name")))
        raise RuntimeError("Water is burning")

    def dump_to_file(self, outfile: str = "jenkins.json") -> bool:
        """Dump report."""
        with open(outfile, "w") as report:
            json.dump(self._report, report, indent=4)
