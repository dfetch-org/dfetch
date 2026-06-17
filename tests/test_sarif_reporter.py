"""Tests for dfetch/reporting/check/sarif_reporter.py."""

# mypy: ignore-errors
# flake8: noqa

import json
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest

from dfetch.manifest.manifest import Manifest, ManifestEntryLocation
from dfetch.manifest.project import ProjectEntry
from dfetch.reporting.check.reporter import Issue, IssueSeverity
from dfetch.reporting.check.sarif_reporter import (
    SarifReporter,
    SarifResultLevel,
    SarifSerializer,
)


def _make_manifest():
    """Return a minimal Manifest mock."""
    manifest = MagicMock(spec=Manifest)
    manifest.path = "/some/dfetch.yaml"
    manifest.find_name_in_manifest.return_value = ManifestEntryLocation(
        line_number=4, start=11, end=13
    )
    return manifest


def _make_reporter():
    """Construct a SarifReporter with a mocked manifest and relpath."""
    manifest = _make_manifest()
    with patch("os.path.relpath", return_value="dfetch.yaml"):
        return SarifReporter(manifest, "/tmp/report.sarif")


def _make_project(name="myproject"):
    project = Mock(spec=ProjectEntry)
    project.name = name
    return project


def _make_issue(severity=IssueSeverity.HIGH, rule_id="unfetched-project"):
    return Issue(
        severity=severity,
        rule_id=rule_id,
        message="Project was never fetched!",
        description="Fetch it.",
    )


# ---------- Severity mapping ----------

def test_severity_to_level_high():
    """IssueSeverity.HIGH maps to SarifResultLevel.ERROR."""
    assert SarifReporter._severity_to_level(IssueSeverity.HIGH) is SarifResultLevel.ERROR


def test_severity_to_level_normal():
    """IssueSeverity.NORMAL maps to SarifResultLevel.WARNING."""
    assert SarifReporter._severity_to_level(IssueSeverity.NORMAL) is SarifResultLevel.WARNING


def test_severity_to_level_low():
    """IssueSeverity.LOW maps to SarifResultLevel.NOTE."""
    assert SarifReporter._severity_to_level(IssueSeverity.LOW) is SarifResultLevel.NOTE


# ---------- add_issue ----------

def test_add_issue_appends_result():
    """After add_issue, _run.results has exactly one item."""
    reporter = _make_reporter()
    reporter.add_issue(_make_project(), _make_issue())
    assert len(reporter._run.results) == 1


def test_add_issue_result_has_correct_level():
    """Result level value is 'error' for HIGH severity."""
    reporter = _make_reporter()
    reporter.add_issue(_make_project(), _make_issue(severity=IssueSeverity.HIGH))
    result = reporter._run.results[0]
    assert result.level == "error"


def test_add_issue_result_has_rule_id():
    """Result rule_id matches the issue's rule_id."""
    reporter = _make_reporter()
    issue = _make_issue(rule_id="unfetched-project")
    reporter.add_issue(_make_project(), issue)
    result = reporter._run.results[0]
    assert result.rule_id == "unfetched-project"


# ---------- dump_to_file ----------

def test_dump_to_file_writes_json():
    """dump_to_file opens the report path and writes JSON content."""
    reporter = _make_reporter()

    m = mock_open()
    with patch("builtins.open", m):
        with patch("json.dump") as mock_json_dump:
            reporter.dump_to_file()

            m.assert_called_once_with("/tmp/report.sarif", "w", encoding="utf-8")
            mock_json_dump.assert_called_once()


# ---------- SarifSerializer._walk_sarif ----------

def _bare_serializer():
    """Create a SarifSerializer instance without calling __init__."""
    instance = SarifSerializer.__new__(SarifSerializer)
    instance._sarif_dict = {}
    return instance


def test_sarif_serializer_walk_int():
    """_walk_sarif passes integers through unchanged."""
    s = _bare_serializer()
    assert s._walk_sarif(42) == 42


def test_sarif_serializer_walk_str():
    """_walk_sarif passes strings through unchanged."""
    s = _bare_serializer()
    assert s._walk_sarif("hello") == "hello"


def test_sarif_serializer_walk_list():
    """_walk_sarif recurses into lists, returning a new list."""
    s = _bare_serializer()
    assert s._walk_sarif([1, 2]) == [1, 2]


def test_sarif_serializer_walk_none():
    """_walk_sarif returns None for None input."""
    s = _bare_serializer()
    assert s._walk_sarif(None) is None


# ---------- CheckReporter methods (inherited by SarifReporter) ----------

from dfetch.manifest.version import Version


def test_unfetched_project_creates_high_severity_issue():
    """unfetched_project adds a HIGH severity issue with rule 'unfetched-project'."""
    reporter = _make_reporter()
    project = _make_project("mylib")
    reporter.unfetched_project(project, Version(branch="main"), Version(branch="main"))
    assert len(reporter._run.results) == 1
    assert reporter._run.results[0].rule_id == "unfetched-project"
    assert reporter._run.results[0].level == "error"


def test_unfetched_project_message_contains_project_name():
    """unfetched_project message names the project."""
    reporter = _make_reporter()
    project = _make_project("coolproject")
    reporter.unfetched_project(project, Version(branch="main"), Version(branch="main"))
    result = reporter._run.results[0]
    assert "coolproject" in result.message.text


def test_unavailable_project_version_creates_low_severity_issue():
    """unavailable_project_version adds a LOW severity issue."""
    reporter = _make_reporter()
    project = _make_project("mylib")
    reporter.unavailable_project_version(project, Version(tag="v1.0"))
    assert len(reporter._run.results) == 1
    assert reporter._run.results[0].rule_id == "unavailable-project-version"
    assert reporter._run.results[0].level == "note"


def test_pinned_but_out_of_date_project_creates_low_severity_issue():
    """pinned_but_out_of_date_project adds a LOW severity issue."""
    reporter = _make_reporter()
    project = _make_project("mylib")
    reporter.pinned_but_out_of_date_project(
        project, Version(tag="v1.0"), Version(tag="v2.0")
    )
    assert len(reporter._run.results) == 1
    assert reporter._run.results[0].rule_id == "pinned-but-out-of-date-project"
    assert reporter._run.results[0].level == "note"


def test_out_of_date_project_creates_normal_severity_issue():
    """out_of_date_project adds a NORMAL severity issue."""
    reporter = _make_reporter()
    project = _make_project("mylib")
    reporter.out_of_date_project(
        project, Version(branch="main"), Version(branch="main"), Version(branch="main")
    )
    assert len(reporter._run.results) == 1
    assert reporter._run.results[0].rule_id == "out-of-date-project"
    assert reporter._run.results[0].level == "warning"


def test_local_changes_creates_normal_severity_issue():
    """local_changes adds a NORMAL severity issue with rule 'local-changes-in-project'."""
    reporter = _make_reporter()
    project = _make_project("mylib")
    reporter.local_changes(project)
    assert len(reporter._run.results) == 1
    assert reporter._run.results[0].rule_id == "local-changes-in-project"
    assert reporter._run.results[0].level == "warning"


def test_up_to_date_project_adds_no_issue():
    """up_to_date_project does not add any issue to the report."""
    reporter = _make_reporter()
    project = _make_project("mylib")
    reporter.up_to_date_project(project, Version(branch="main"))
    assert len(reporter._run.results) == 0
