"""Tests for dfetch.reporting.check.stdout_reporter.CheckStdoutReporter."""

# mypy: ignore-errors
# flake8: noqa

from unittest.mock import MagicMock, Mock, patch

from dfetch.manifest.project import ProjectEntry
from dfetch.manifest.version import Version
from dfetch.reporting.check.reporter import Issue, IssueSeverity
from dfetch.reporting.check.stdout_reporter import CheckStdoutReporter


def _make_manifest():
    manifest = MagicMock()
    manifest.path = "/some/dfetch.yaml"
    return manifest


def _make_project(name="mylib"):
    project = Mock(spec=ProjectEntry)
    project.name = name
    return project


def _make_reporter():
    return CheckStdoutReporter(_make_manifest())


def test_unfetched_project_logs_with_wanted():
    reporter = _make_reporter()
    project = _make_project()
    with patch("dfetch.reporting.check.stdout_reporter.logger") as mock_logger:
        reporter.unfetched_project(
            project, Version(branch="main"), Version(branch="main")
        )
        mock_logger.print_info_line.assert_called_once()
        assert "main" in mock_logger.print_info_line.call_args[0][1]


def test_unfetched_project_omits_wanted_when_empty():
    reporter = _make_reporter()
    project = _make_project()
    with patch("dfetch.reporting.check.stdout_reporter.logger") as mock_logger:
        reporter.unfetched_project(project, Version(), Version(branch="main"))
        assert "wanted" not in mock_logger.print_info_line.call_args[0][1]


def test_up_to_date_project_logs_info():
    reporter = _make_reporter()
    project = _make_project()
    with patch("dfetch.reporting.check.stdout_reporter.logger") as mock_logger:
        reporter.up_to_date_project(project, Version(branch="main"))
        assert "up-to-date" in mock_logger.print_info_line.call_args[0][1]


def test_unavailable_project_version_logs_info():
    reporter = _make_reporter()
    project = _make_project()
    with patch("dfetch.reporting.check.stdout_reporter.logger") as mock_logger:
        reporter.unavailable_project_version(project, Version(tag="v1.0"))
        mock_logger.print_info_line.assert_called_once()


def test_pinned_but_out_of_date_logs_info():
    reporter = _make_reporter()
    project = _make_project()
    with patch("dfetch.reporting.check.stdout_reporter.logger") as mock_logger:
        reporter.pinned_but_out_of_date_project(
            project, Version(tag="v1.0"), Version(tag="v2.0")
        )
        assert "available" in mock_logger.print_info_line.call_args[0][1]


def test_out_of_date_project_logs_info():
    reporter = _make_reporter()
    project = _make_project()
    with patch("dfetch.reporting.check.stdout_reporter.logger") as mock_logger:
        reporter.out_of_date_project(
            project,
            Version(branch="main"),
            Version(branch="main"),
            Version(branch="main"),
        )
        mock_logger.print_info_line.assert_called_once()


def test_local_changes_logs_warning():
    reporter = _make_reporter()
    project = _make_project("mylib")
    with patch("dfetch.reporting.check.stdout_reporter.logger") as mock_logger:
        reporter.local_changes(project)
        args = mock_logger.print_warning_line.call_args[0]
        assert "dfetch diff" in args[1]


def test_add_issue_does_not_raise():
    reporter = _make_reporter()
    issue = Issue(
        severity=IssueSeverity.HIGH, rule_id="x", message="msg", description="desc"
    )
    reporter.add_issue(_make_project(), issue)


def test_dump_to_file_does_not_raise():
    reporter = _make_reporter()
    reporter.dump_to_file()
