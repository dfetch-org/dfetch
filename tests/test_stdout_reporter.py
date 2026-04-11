"""Unit tests for dfetch.reporting.stdout_reporter – LicenseScanResult integration."""

# mypy: ignore-errors
# flake8: noqa

from unittest.mock import MagicMock, Mock, patch

import pytest

from dfetch.manifest.project import ProjectEntry
from dfetch.reporting.stdout_reporter import StdoutReporter
from dfetch.util.license import License, LicenseScanResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_project(name: str = "my-project") -> Mock:
    p = Mock(spec=ProjectEntry)
    p.name = name
    p.remote = ""
    p.destination = name
    return p


def _make_license(name: str, spdx_id: str = "MIT", probability: float = 0.95) -> License:
    return License(name=name, spdx_id=spdx_id, trove_classifier=None, probability=probability)


def _make_manifest() -> MagicMock:
    m = MagicMock()
    return m


# ---------------------------------------------------------------------------
# StdoutReporter.add_project – licenses display
# ---------------------------------------------------------------------------


def test_add_project_with_empty_identified_list_prints_empty_licenses():
    """When no licenses are identified the licenses field is printed as empty."""
    reporter = StdoutReporter(_make_manifest())
    project = _make_project()
    scan = LicenseScanResult(was_scanned=True)

    with patch("dfetch.reporting.stdout_reporter.logger") as mock_logger, patch(
        "dfetch.project.metadata.Metadata.from_file"
    ) as mock_meta:
        mock_metadata = MagicMock()
        mock_metadata.dependencies = []
        mock_metadata.patch = []
        mock_meta.return_value = mock_metadata

        reporter.add_project(project=project, license_scan=scan, version="1.0")

        # The 'licenses' field should be called with an empty string
        calls = [
            call for call in mock_logger.print_info_field.call_args_list
            if call.args[0] == "  licenses"
        ]
        assert calls, "print_info_field was not called with '  licenses'"
        licenses_value = calls[0].args[1]
        assert licenses_value == ""


def test_add_project_with_identified_licenses_prints_names():
    """Identified license names are joined and printed."""
    reporter = StdoutReporter(_make_manifest())
    project = _make_project()
    lic = _make_license(name="MIT License")
    scan = LicenseScanResult(identified=[lic], was_scanned=True)

    with patch("dfetch.reporting.stdout_reporter.logger") as mock_logger, patch(
        "dfetch.project.metadata.Metadata.from_file"
    ) as mock_meta:
        mock_metadata = MagicMock()
        mock_metadata.dependencies = []
        mock_metadata.patch = []
        mock_meta.return_value = mock_metadata

        reporter.add_project(project=project, license_scan=scan, version="1.0")

        calls = [
            call for call in mock_logger.print_info_field.call_args_list
            if call.args[0] == "  licenses"
        ]
        assert calls
        licenses_value = calls[0].args[1]
        assert "MIT License" in licenses_value


def test_add_project_with_multiple_identified_licenses_joins_names():
    """Multiple license names are comma-joined."""
    reporter = StdoutReporter(_make_manifest())
    project = _make_project()
    lic1 = _make_license(name="MIT License")
    lic2 = _make_license(name="Apache Software License", spdx_id="Apache-2.0")
    scan = LicenseScanResult(identified=[lic1, lic2], was_scanned=True)

    with patch("dfetch.reporting.stdout_reporter.logger") as mock_logger, patch(
        "dfetch.project.metadata.Metadata.from_file"
    ) as mock_meta:
        mock_metadata = MagicMock()
        mock_metadata.dependencies = []
        mock_metadata.patch = []
        mock_meta.return_value = mock_metadata

        reporter.add_project(project=project, license_scan=scan, version="1.0")

        calls = [
            call for call in mock_logger.print_info_field.call_args_list
            if call.args[0] == "  licenses"
        ]
        assert calls
        licenses_value = calls[0].args[1]
        assert "MIT License" in licenses_value
        assert "Apache Software License" in licenses_value


def test_add_project_not_scanned_uses_identified_empty():
    """When was_scanned=False, identified is empty so licenses field is blank."""
    reporter = StdoutReporter(_make_manifest())
    project = _make_project()
    scan = LicenseScanResult(was_scanned=False)

    with patch("dfetch.reporting.stdout_reporter.logger") as mock_logger, patch(
        "dfetch.project.metadata.Metadata.from_file"
    ) as mock_meta:
        mock_metadata = MagicMock()
        mock_metadata.dependencies = []
        mock_metadata.patch = []
        mock_meta.return_value = mock_metadata

        reporter.add_project(project=project, license_scan=scan, version="1.0")

        calls = [
            call for call in mock_logger.print_info_field.call_args_list
            if call.args[0] == "  licenses"
        ]
        assert calls
        licenses_value = calls[0].args[1]
        assert licenses_value == ""


def test_add_project_unclassified_only_prints_empty_licenses():
    """Unclassified files do not appear in the licenses field for stdout."""
    reporter = StdoutReporter(_make_manifest())
    project = _make_project()
    scan = LicenseScanResult(unclassified_files=["LICENSE"], was_scanned=True)

    with patch("dfetch.reporting.stdout_reporter.logger") as mock_logger, patch(
        "dfetch.project.metadata.Metadata.from_file"
    ) as mock_meta:
        mock_metadata = MagicMock()
        mock_metadata.dependencies = []
        mock_metadata.patch = []
        mock_meta.return_value = mock_metadata

        reporter.add_project(project=project, license_scan=scan, version="1.0")

        calls = [
            call for call in mock_logger.print_info_field.call_args_list
            if call.args[0] == "  licenses"
        ]
        assert calls
        licenses_value = calls[0].args[1]
        assert licenses_value == ""