"""*Dfetch* can generate a report that is parsable by GitLab/Code Climate from the :ref:`check` results.

Depending on the state of the projects it will create a report with information.
If all project are up-to-date, nothing will be added to the report.

The information has several severities:

* ``major`` : An unfetched project. Fetch the project to solve the issue.
* ``minor`` : An out-of-date project. The project is not pinned and a newer version is available.
* ``info`` : a pinned but out-of-date project. The project is pinned to a specific version,
            but a newer version is available.

The report generated is the `code-climate json format`_, the fields described in the
`gitlab custom code quality tool`_ documentation are in the report but also all fields
listed as required by the `code-climate json format`_.

Gitlab will show the results with the pipeline

.. image:: images/gitlab-check-pipeline-result.png
    :alt: Gitlab detected issues.

And clicking will bring you to the project in the manifest.

.. image:: images/gitlab-highlighted-manifest.png
    :alt: Gitlab highlights the project in the manifest with the issue.

In the merge request, GitLab will compare the issues in the current branch with those of
the base branch (e.g. ``master``/``main``). This lets you see if any new issue were introduced
or solved.

.. scenario-include:: ../features/check-report-code-climate.feature

Usage
-----
Let *DFetch* perform a check and generate the code-climate json and add the result as artifact in your gitlab-ci runner.
See `gitlab code quality reports`_ for more information.

.. code-block:: yaml

    dfetch:
      image: "python:3.13"
      script:
      - pip install dfetch
      - dfetch check --code-climate dfetch.json
      artifacts:
        reports:
          codequality: dfetch.json


.. _`code-climate json format`: https://github.com/codeclimate/platform/blob/master/spec/analyzers/SPEC.md#data-types
.. _`gitlab custom code quality tool`:
    https://docs.gitlab.com/ee/user/project/merge_requests/code_quality.html#implementing-a-custom-tool
.. _`gitlab code quality reports`: https://docs.gitlab.com/ee/ci/yaml/artifacts_reports.html#artifactsreportscodequality

"""

import hashlib
import json
import os
from enum import Enum
from typing import Any

from dfetch.log import get_logger
from dfetch.manifest.manifest import Manifest
from dfetch.manifest.project import ProjectEntry
from dfetch.reporting.check.reporter import CheckReporter, Issue, IssueSeverity

logger = get_logger(__name__)


class CodeClimateSeverity(Enum):
    """Code climate result level."""

    BLOCKER = "blocker"
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"


class CodeClimateReporter(CheckReporter):
    """Reporter for generating report on stdout."""

    name = "code-climate"

    def __init__(self, manifest: Manifest, report_path: str) -> None:
        """Create the code climate reporter.

        Args:
            manifest (Manifest): The manifest.
            report_path (str): Output path of the report.
        """
        super().__init__(manifest)

        self._report_path = report_path

        self._report: list[dict[str, Any]] = []

    @staticmethod
    def _determine_severity(severity: IssueSeverity) -> CodeClimateSeverity:
        """Convert a generic issue severity to specific code climate level."""
        return {
            "HIGH": CodeClimateSeverity.MAJOR,
            "NORMAL": CodeClimateSeverity.MINOR,
            "LOW": CodeClimateSeverity.INFO,
        }[severity.name]

    def add_issue(self, project: ProjectEntry, issue: Issue) -> None:
        """Add an issue to the report.

        Args:
            project (ProjectEntry): Project with the issue
            issue (Issue): The issue to add to the report
        """
        location = self._manifest.find_name_in_manifest(project.name)

        self._report += [
            {
                "description": issue.description,
                "check_name": issue.rule_id,
                "categories": ["Security", "Bug risk"],
                "fingerprint": hashlib.sha256(
                    f"{project.name}{issue.rule_id}".encode(encoding="utf-8")
                ).hexdigest(),
                "severity": self._determine_severity(issue.severity).value,
                "location": {
                    "path": os.path.relpath(self._manifest.path),
                    "positions": {
                        "begin": {
                            "line": location.line_number,
                            "column": location.start,
                        },
                        "end": {"line": location.line_number, "column": location.end},
                    },
                },
            }
        ]

    def dump_to_file(self) -> None:
        """Dump report."""
        with open(self._report_path, "w", encoding="utf-8") as report:
            json.dump(self._report, report, indent=4)
