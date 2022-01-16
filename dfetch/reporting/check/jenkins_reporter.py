"""*Dfetch* can generate a report that is parseable by Jenkins from the :ref:`check` results.

Dependending on the state of the projects it will create a report with information.
If all project are up-to-date, nothing will be added to the report.

The information has several severities:

* ``high`` : An unfetched project. Fetch the project to solve the issue.
* ``normal`` : An out-of-date project. The project is not pinned and a newer version is available.
* ``low`` : An pinned but out-of-date project. The project is pinned to a specific version,
            but a newer version is available.

The report generated is the `native json format`_ of the `warnings-ng plugin`_. The plugin will
show an overview of the found issues:

.. image:: images/out-of-date-jenkins2.png
    :alt: Cpputest is out-of-date and requires updating.

When an issues is clicked, you can see the exact location in the manifest where the project is listed.

.. image:: images/out-of-date-jenkins.png
    :alt: Cpputest is out-of-date and requires updating.

Usage
-----

Add to pipeline using `warnings-ng plugin`_:

.. code-block:: groovy

    /* For a windows agent */
    bat: 'dfetch check --jenkins-json jenkins.json'

    /* For a linux agent */
    sh: 'dfetch check --jenkins-json jenkins.json'

    recordIssues tool: issues(pattern: 'jenkins.json', name: 'DFetch')

With the `warnings-ng plugin`_ quality gates thresholds can be set to influence the build result.
For example don't fail when pinned projects are out-of-date.For more information see the
`quality gate configuration`_ documentation of the `warnings-ng plugin`_.

.. _`warnings-ng plugin`: https://plugins.jenkins.io/warnings-ng/
.. _`native json format`: https://github.com/jenkinsci/warnings-ng-plugin/blob/master/doc/Documentation.md\
#export-your-issues-into-a-supported-format
.. _`quality gate configuration`: https://github.com/jenkinsci/warnings-ng-plugin/blob/master\
/doc/Documentation.md#quality-gate-configuration

"""

import json
import os
import re
from typing import Any, Dict, Tuple

from dfetch.log import get_logger
from dfetch.manifest.project import ProjectEntry
from dfetch.manifest.version import Version
from dfetch.reporting.check.reporter import CheckReporter

logger = get_logger(__name__)


class JenkinsReporter(CheckReporter):
    """Reporter for generating report on stdout."""

    name = "jenkins"

    def __init__(self, manifest_path: str, report_path: str) -> None:
        """Create the jenkins reporter.

        Args:
            manifest_path (str): Path to the manifest.
            report_path (str): Output path of the report.
        """
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
        self._add_issue(project, "Low", msg, description)

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
        with open(self._report_path, "w", encoding="utf-8") as report:
            json.dump(self._report, report, indent=4)
