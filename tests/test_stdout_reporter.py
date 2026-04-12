"""Tests for dfetch.reporting.stdout_reporter (PR #1112 license_scan changes)."""

# mypy: ignore-errors
# flake8: noqa

from unittest.mock import MagicMock, patch

import pytest

from dfetch.reporting.stdout_reporter import StdoutReporter
from dfetch.util.license import License, LicenseScanResult


def _make_manifest():
    manifest = MagicMock()
    return manifest


def _make_project(name: str = "my-project", destination: str = "/tmp/my-project"):
    project = MagicMock()
    project.name = name
    project.destination = destination
    project.remote = "origin"
    return project


def _make_metadata():
    meta = MagicMock()
    meta.remote_url = "https://example.com/repo.git"
    meta.branch = "main"
    meta.tag = ""
    meta.last_fetch = "01/01/2024, 12:00:00"
    meta.revision = "abc123"
    meta.patch = []
    meta.dependencies = []
    return meta


# ---------------------------------------------------------------------------
# StdoutReporter.add_project – license_scan.identified is used for licenses
# ---------------------------------------------------------------------------


def test_add_project_prints_identified_license_name():
    reporter = StdoutReporter(_make_manifest())
    project = _make_project()
    lic = License(
        name="MIT License", spdx_id="MIT", trove_classifier=None, probability=0.99
    )
    scan = LicenseScanResult(identified=[lic], was_scanned=True, threshold=0.80)

    meta = _make_metadata()
    with patch(
        "dfetch.reporting.stdout_reporter.Metadata.from_file", return_value=meta
    ):
        with patch(
            "dfetch.reporting.stdout_reporter.Metadata.from_project_entry",
            return_value=MagicMock(path="/tmp/.dfetch_data.yaml"),
        ):
            with patch(
                "dfetch.reporting.stdout_reporter.logger.print_info_field"
            ) as mock_field:
                reporter.add_project(project=project, license_scan=scan, version="1.0")

    calls = {call[0][0]: call[0][1] for call in mock_field.call_args_list}
    assert "  licenses" in calls
    assert "MIT License" in calls["  licenses"]


def test_add_project_prints_empty_licenses_when_no_identified():
    reporter = StdoutReporter(_make_manifest())
    project = _make_project()
    scan = LicenseScanResult(was_scanned=True, threshold=0.80)

    meta = _make_metadata()
    with patch(
        "dfetch.reporting.stdout_reporter.Metadata.from_file", return_value=meta
    ):
        with patch(
            "dfetch.reporting.stdout_reporter.Metadata.from_project_entry",
            return_value=MagicMock(path="/tmp/.dfetch_data.yaml"),
        ):
            with patch(
                "dfetch.reporting.stdout_reporter.logger.print_info_field"
            ) as mock_field:
                reporter.add_project(project=project, license_scan=scan, version="1.0")

    calls = {call[0][0]: call[0][1] for call in mock_field.call_args_list}
    assert "  licenses" in calls
    assert calls["  licenses"] == ""


def test_add_project_prints_multiple_licenses_comma_separated():
    reporter = StdoutReporter(_make_manifest())
    project = _make_project()
    lic1 = License(
        name="MIT License", spdx_id="MIT", trove_classifier=None, probability=0.99
    )
    lic2 = License(
        name="Apache Software License",
        spdx_id="Apache-2.0",
        trove_classifier=None,
        probability=0.92,
    )
    scan = LicenseScanResult(
        identified=[lic1, lic2], was_scanned=True, threshold=0.80
    )

    meta = _make_metadata()
    with patch(
        "dfetch.reporting.stdout_reporter.Metadata.from_file", return_value=meta
    ):
        with patch(
            "dfetch.reporting.stdout_reporter.Metadata.from_project_entry",
            return_value=MagicMock(path="/tmp/.dfetch_data.yaml"),
        ):
            with patch(
                "dfetch.reporting.stdout_reporter.logger.print_info_field"
            ) as mock_field:
                reporter.add_project(project=project, license_scan=scan, version="1.0")

    calls = {call[0][0]: call[0][1] for call in mock_field.call_args_list}
    assert "  licenses" in calls
    license_output = calls["  licenses"]
    assert "MIT License" in license_output
    assert "Apache Software License" in license_output
    assert "," in license_output


def test_add_project_not_fetched_shows_never(tmp_path):
    """When metadata file is absent (not fetched), 'last fetch: never' is shown."""
    reporter = StdoutReporter(_make_manifest())
    project = _make_project()
    scan = LicenseScanResult(was_scanned=False)

    with patch(
        "dfetch.reporting.stdout_reporter.Metadata.from_file",
        side_effect=FileNotFoundError,
    ):
        with patch(
            "dfetch.reporting.stdout_reporter.Metadata.from_project_entry",
            return_value=MagicMock(path="/tmp/.dfetch_data.yaml"),
        ):
            with patch(
                "dfetch.reporting.stdout_reporter.logger.print_info_field"
            ) as mock_field:
                reporter.add_project(project=project, license_scan=scan, version="1.0")

    calls = {call[0][0]: call[0][1] for call in mock_field.call_args_list}
    assert "  last fetch" in calls
    assert calls["  last fetch"] == "never"


def test_add_project_unclassified_files_not_shown_in_stdout():
    """Unclassified files don't appear in stdout – only identified licenses are shown."""
    reporter = StdoutReporter(_make_manifest())
    project = _make_project()
    scan = LicenseScanResult(
        unclassified_files=["LICENSE"],
        was_scanned=True,
        threshold=0.80,
    )

    meta = _make_metadata()
    with patch(
        "dfetch.reporting.stdout_reporter.Metadata.from_file", return_value=meta
    ):
        with patch(
            "dfetch.reporting.stdout_reporter.Metadata.from_project_entry",
            return_value=MagicMock(path="/tmp/.dfetch_data.yaml"),
        ):
            with patch(
                "dfetch.reporting.stdout_reporter.logger.print_info_field"
            ) as mock_field:
                reporter.add_project(project=project, license_scan=scan, version="1.0")

    calls = {call[0][0]: call[0][1] for call in mock_field.call_args_list}
    # License field should be empty because no identified licenses
    assert calls.get("  licenses", "") == ""


def test_dump_to_file_returns_false():
    """StdoutReporter.dump_to_file should always return False (no file written)."""
    reporter = StdoutReporter(_make_manifest())
    assert reporter.dump_to_file("report.json") is False