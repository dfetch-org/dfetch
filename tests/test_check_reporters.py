"""Tests for Jenkins and Code Climate check reporters."""

# mypy: ignore-errors
# flake8: noqa

import json
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest

from dfetch.manifest.manifest import Manifest, ManifestEntryLocation
from dfetch.manifest.project import ProjectEntry
from dfetch.reporting.check.code_climate_reporter import (
    CodeClimateReporter,
    CodeClimateSeverity,
)
from dfetch.reporting.check.jenkins_reporter import JenkinsReporter
from dfetch.reporting.check.reporter import Issue, IssueSeverity


def _make_manifest():
    manifest = MagicMock(spec=Manifest)
    manifest.path = "/some/dfetch.yaml"
    manifest.find_name_in_manifest.return_value = ManifestEntryLocation(
        line_number=4, start=11, end=13
    )
    return manifest


def _make_project(name="myproject"):
    project = Mock(spec=ProjectEntry)
    project.name = name
    return project


def _make_issue(
    severity=IssueSeverity.HIGH, rule_id="unfetched-project", message="never fetched"
):
    return Issue(
        severity=severity,
        rule_id=rule_id,
        message=message,
        description="Fetch it.",
    )


# ==================
# JenkinsReporter
# ==================


def test_jenkins_reporter_init_creates_empty_issues():
    """JenkinsReporter starts with an empty issues list."""
    with patch("os.path.relpath", return_value="dfetch.yaml"):
        reporter = JenkinsReporter(_make_manifest(), "/tmp/jenkins.json")
    assert reporter._report["issues"] == []


def test_jenkins_add_issue_appends_entry():
    """add_issue appends one item to the issues list."""
    with patch("os.path.relpath", return_value="dfetch.yaml"):
        reporter = JenkinsReporter(_make_manifest(), "/tmp/jenkins.json")
    with patch("os.path.relpath", return_value="dfetch.yaml"):
        reporter.add_issue(_make_project(), _make_issue())
    assert len(reporter._report["issues"]) == 1


def test_jenkins_add_issue_contains_severity():
    """add_issue records the severity string."""
    with patch("os.path.relpath", return_value="dfetch.yaml"):
        reporter = JenkinsReporter(_make_manifest(), "/tmp/jenkins.json")
    with patch("os.path.relpath", return_value="dfetch.yaml"):
        reporter.add_issue(
            _make_project("mymod"), _make_issue(severity=IssueSeverity.HIGH)
        )
    entry = reporter._report["issues"][0]
    assert entry["severity"] == "High"


def test_jenkins_add_issue_contains_project_name():
    """add_issue records the project name in the message."""
    with patch("os.path.relpath", return_value="dfetch.yaml"):
        reporter = JenkinsReporter(_make_manifest(), "/tmp/jenkins.json")
    with patch("os.path.relpath", return_value="dfetch.yaml"):
        reporter.add_issue(_make_project("specialmod"), _make_issue())
    entry = reporter._report["issues"][0]
    assert "specialmod" in entry["message"]


def test_jenkins_dump_to_file_writes_json():
    """dump_to_file writes valid JSON to the report path."""
    with patch("os.path.relpath", return_value="dfetch.yaml"):
        reporter = JenkinsReporter(_make_manifest(), "/tmp/jenkins.json")

    m = mock_open()
    with patch("builtins.open", m):
        with patch("json.dump") as mock_json_dump:
            reporter.dump_to_file()
            m.assert_called_once_with("/tmp/jenkins.json", "w", encoding="utf-8")
            mock_json_dump.assert_called_once()


# ==================
# CodeClimateReporter
# ==================


def test_code_climate_severity_high_maps_to_major():
    """HIGH severity maps to CodeClimateSeverity.MAJOR."""
    assert (
        CodeClimateReporter._determine_severity(IssueSeverity.HIGH)
        == CodeClimateSeverity.MAJOR
    )


def test_code_climate_severity_normal_maps_to_minor():
    """NORMAL severity maps to CodeClimateSeverity.MINOR."""
    assert (
        CodeClimateReporter._determine_severity(IssueSeverity.NORMAL)
        == CodeClimateSeverity.MINOR
    )


def test_code_climate_severity_low_maps_to_info():
    """LOW severity maps to CodeClimateSeverity.INFO."""
    assert (
        CodeClimateReporter._determine_severity(IssueSeverity.LOW)
        == CodeClimateSeverity.INFO
    )


def test_code_climate_add_issue_appends_entry():
    """add_issue appends one item to the report list."""
    with patch("os.path.relpath", return_value="dfetch.yaml"):
        reporter = CodeClimateReporter(_make_manifest(), "/tmp/cc.json")
    with patch("os.path.relpath", return_value="dfetch.yaml"):
        reporter.add_issue(_make_project(), _make_issue())
    assert len(reporter._report) == 1


def test_code_climate_add_issue_contains_check_name():
    """add_issue records the rule_id as check_name."""
    with patch("os.path.relpath", return_value="dfetch.yaml"):
        reporter = CodeClimateReporter(_make_manifest(), "/tmp/cc.json")
    with patch("os.path.relpath", return_value="dfetch.yaml"):
        reporter.add_issue(_make_project(), _make_issue(rule_id="unfetched-project"))
    entry = reporter._report[0]
    assert entry["check_name"] == "unfetched-project"


def test_code_climate_add_issue_severity_value():
    """add_issue records the correct severity string for HIGH."""
    with patch("os.path.relpath", return_value="dfetch.yaml"):
        reporter = CodeClimateReporter(_make_manifest(), "/tmp/cc.json")
    with patch("os.path.relpath", return_value="dfetch.yaml"):
        reporter.add_issue(_make_project(), _make_issue(severity=IssueSeverity.HIGH))
    entry = reporter._report[0]
    assert entry["severity"] == "major"


def test_code_climate_dump_to_file_writes_json():
    """dump_to_file writes valid JSON to the report path."""
    with patch("os.path.relpath", return_value="dfetch.yaml"):
        reporter = CodeClimateReporter(_make_manifest(), "/tmp/cc.json")

    m = mock_open()
    with patch("builtins.open", m):
        with patch("json.dump") as mock_json_dump:
            reporter.dump_to_file()
            m.assert_called_once_with("/tmp/cc.json", "w", encoding="utf-8")
            mock_json_dump.assert_called_once()


def test_code_climate_fingerprint_is_deterministic():
    """The fingerprint for the same project/issue is the same each time."""
    with patch("os.path.relpath", return_value="dfetch.yaml"):
        reporter1 = CodeClimateReporter(_make_manifest(), "/tmp/cc.json")
        reporter2 = CodeClimateReporter(_make_manifest(), "/tmp/cc.json")

    with patch("os.path.relpath", return_value="dfetch.yaml"):
        reporter1.add_issue(_make_project("mymod"), _make_issue())
        reporter2.add_issue(_make_project("mymod"), _make_issue())

    assert reporter1._report[0]["fingerprint"] == reporter2._report[0]["fingerprint"]
