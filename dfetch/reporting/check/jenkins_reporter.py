"""*Dfetch* can generate a report that is parseable by Jenkins from the :ref:`check` results.

Depending on the state of the projects it will create a report with information.
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
from typing import Any, Dict

from dfetch.log import get_logger
from dfetch.manifest.project import ProjectEntry
from dfetch.reporting.check.reporter import CheckReporter, Issue

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
        super().__init__(manifest_path)

        self._report_path = report_path

        self._report: Dict[str, Any] = {
            "_class": "io.jenkins.plugins.analysis.core.restapi.ReportApi",
            "issues": [],
        }

    def add_issue(self, project: ProjectEntry, issue: Issue) -> None:
        """Add an issue to the report.

        Args:
            project (ProjectEntry): Project with the issue
            issue (Issue): The issue to add to the report
        """
        line, col_start, col_end = self.find_name_in_manifest(project.name)
        self._report["issues"] += [
            {
                "fileName": os.path.relpath(self._manifest_path),
                "severity": str(issue.severity.value),
                "message": f"{project.name} : {issue.message}",
                "description": issue.description,
                "lineStart": line,
                "lineEnd": line,
                "columnStart": col_start,
                "columnEnd": col_end,
            }
        ]

    def dump_to_file(self) -> None:
        """Dump report."""
        with open(self._report_path, "w", encoding="utf-8") as report:
            json.dump(self._report, report, indent=4)
