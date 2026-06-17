"""Tests for dfetch.reporting.check.jenkins_reporter.JenkinsReporter."""

# mypy: ignore-errors
# flake8: noqa

import json
from unittest.mock import MagicMock, Mock, mock_open, patch

from dfetch.manifest.manifest import Manifest, ManifestEntryLocation
from dfetch.manifest.project import ProjectEntry
from dfetch.reporting.check.jenkins_reporter import JenkinsReporter
from dfetch.reporting.check.reporter import Issue, IssueSeverity


def _make_manifest():
    manifest = MagicMock(spec=Manifest)
    manifest.path = "/some/dfetch.yaml"
    manifest.find_name_in_manifest.return_value = ManifestEntryLocation(
        line_number=4, start=11, end=13
    )
    return manifest


def _make_reporter():
    with patch("os.path.relpath", return_value="dfetch.yaml"):
        return JenkinsReporter(_make_manifest(), "/tmp/jenkins.json")


def _make_project(name="mylib"):
    project = Mock(spec=ProjectEntry)
    project.name = name
    return project


def _make_issue(severity=IssueSeverity.HIGH, rule_id="unfetched-project"):
    return Issue(
        severity=severity,
        rule_id=rule_id,
        message="never fetched",
        description="fetch it",
    )


def test_add_issue_appends_to_report():
    reporter = _make_reporter()
    reporter.add_issue(_make_project(), _make_issue())
    assert len(reporter._report["issues"]) == 1


def test_add_issue_severity_is_string():
    reporter = _make_reporter()
    reporter.add_issue(_make_project(), _make_issue(severity=IssueSeverity.NORMAL))
    issue = reporter._report["issues"][0]
    assert isinstance(issue["severity"], str)
    assert "Normal" in issue["severity"]


def test_add_issue_message_contains_project_name():
    reporter = _make_reporter()
    reporter.add_issue(_make_project("coolproject"), _make_issue())
    assert "coolproject" in reporter._report["issues"][0]["message"]


def test_add_issue_line_numbers_from_manifest():
    reporter = _make_reporter()
    reporter.add_issue(_make_project(), _make_issue())
    issue = reporter._report["issues"][0]
    assert issue["lineStart"] == 4
    assert issue["columnStart"] == 11
    assert issue["columnEnd"] == 13


def test_dump_to_file_writes_json():
    reporter = _make_reporter()
    reporter.add_issue(_make_project(), _make_issue())

    m = mock_open()
    with patch("builtins.open", m):
        with patch("json.dump") as mock_json_dump:
            reporter.dump_to_file()
            m.assert_called_once_with("/tmp/jenkins.json", "w", encoding="utf-8")
            mock_json_dump.assert_called_once()


def test_report_has_correct_class_key():
    reporter = _make_reporter()
    assert "_class" in reporter._report
    assert (
        reporter._report["_class"]
        == "io.jenkins.plugins.analysis.core.restapi.ReportApi"
    )
