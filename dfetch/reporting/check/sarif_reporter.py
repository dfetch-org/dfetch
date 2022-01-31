"""*Dfetch* can generate a report in the Sarif format that is by Github from the :ref:`check` results.

Dependending on the state of the projects it will create a report with information.
If all project are up-to-date, nothing will be added to the report.

The information has several severities:

* ``high`` : An unfetched project. Fetch the project to solve the issue.
* ``normal`` : An out-of-date project. The project is not pinned and a newer version is available.
* ``low`` : An pinned but out-of-date project. The project is pinned to a specific version,
            but a newer version is available.

Usage
-----

A Sarif report can be added to a github action as such:

.. code-block:: yaml

    - run: dfetch check --sarif sarif.json
    - name: Upload SARIF file
        uses: github/codeql-action/upload-sarif@v1
        with:
            sarif_file: sarif.json

For more information see the `Github Sarif documentation`_.

.. _`Github Sarif documentation` : https://docs.github.com/en/code-security/code-scanning/integrating-with-code-scanning

"""

import json
import os
from typing import Any, Dict

import attr
from sarif_om import (
    Artifact,
    ArtifactLocation,
    Location,
    Message,
    MultiformatMessageString,
    PhysicalLocation,
    Region,
    ReportingDescriptor,
    Result,
    Run,
    SarifLog,
    Tool,
    ToolComponent,
)

from dfetch.log import get_logger
from dfetch.manifest.project import ProjectEntry
from dfetch.reporting.check.reporter import CheckReporter, Issue

logger = get_logger(__name__)


class SarifReporter(CheckReporter):
    """Reporter for generating report in sarif format."""

    name = "sarif"

    VERSION = "2.1.0"
    SCHEMA = (
        "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/"
        "master/Documents/CommitteeSpecifications/2.1.0/sarif-schema-2.1.0.json"
    )

    def __init__(self, manifest_path: str, report_path: str) -> None:
        """Create the sarif reporter.

        Args:
            manifest_path (str): Path to the manifest.
            report_path (str): Output path of the report.
        """
        super().__init__(manifest_path)

        self._report_path = report_path

        self._run = Run(
            tool=Tool(
                driver=ToolComponent(
                    name="DFetch",
                    information_uri="https://dfetch.rtfd.io",
                    rules=[
                        ReportingDescriptor(
                            id=rule.name,
                            short_description=MultiformatMessageString(
                                text=rule.description
                            ),
                        )
                        for rule in self.rules
                    ],
                )
            )
        )
        self._run.artifacts = [
            Artifact(
                location=ArtifactLocation(uri=os.path.relpath(self._manifest_path)),
                source_language="yaml",
            )
        ]
        self._run.results = []
        self._run.newline_sequences = None

    def add_issue(self, project: ProjectEntry, issue: Issue) -> None:
        """Add an issue to the report.

        Args:
            project (ProjectEntry): Project with the issue
            issue (Issue): The issue to add
        """
        line, col_start, col_end = self.find_name_in_manifest(project.name)

        result = Result(
            message=Message(text=f"{project.name} : {issue.message}"),
            level=issue.severity.value,
            rule_id=issue.rule_id,
            locations=[
                Location(
                    physical_location=PhysicalLocation(
                        artifact_location=ArtifactLocation(
                            uri=os.path.relpath(self._manifest_path), index=0
                        ),
                        region=Region(
                            start_line=line,
                            start_column=col_start,
                            end_line=line,
                            end_column=col_end,
                        ),
                    )
                )
            ],
        )

        self._run.results += [result]

    def dump_to_file(self) -> None:
        """Dump report."""
        log = SarifLog(runs=[self._run], version=self.VERSION)
        SarifSerializer(log).dump(self._report_path)


class SarifSerializer:
    """Class for converting a SarifLog to a json."""

    def __init__(self, sarif: SarifLog) -> None:
        """Create a serialized Sarif log.

        Args:
            sarif (SarifLog): Log to serialize
        """
        self._sarif_dict: Dict[str, Any] = {}
        self._json = self._walk_sarif(
            attr.asdict(
                sarif,
                filter=self._filter_unused,
                value_serializer=self._serialize_value,
            )
        )

    @property
    def json(self) -> Any:
        """Get the serialized json."""
        return self._json

    def dump(self, path: str) -> None:
        """Dump the sarif to file."""
        with open(path, "w", encoding="utf-8") as report:
            json.dump(self._json, report, indent=4)

    def _walk_sarif(self, sarif_node: Any) -> Any:
        """Recursively walk through sarif to create readable dictionary."""
        if isinstance(sarif_node, (int, str)):
            return sarif_node
        if isinstance(sarif_node, dict):
            try:
                return {
                    self._sarif_dict[key]: self._walk_sarif(value)
                    for key, value in sarif_node.items()
                }
            except KeyError:
                print(self._sarif_dict)
                raise
        if isinstance(sarif_node, list):
            return [self._walk_sarif(item) for item in sarif_node]
        return None

    def _serialize_value(self, _: Any, field: Any, value: Any) -> Any:
        """Convert the field name into the schema name."""
        if field is not None:
            self._sarif_dict[field.name] = field.metadata["schema_property_name"]
        return value

    def _filter_unused(  # pylint: disable=no-self-use
        self, field: Any, value: Any
    ) -> bool:
        """Filter out the unused."""
        return not (
            value is None
            or (field.default == value and field.name != "level")
            or (
                isinstance(field.default, attr.Factory)  # type:ignore
                and field.default.factory() == value
            )
        )
