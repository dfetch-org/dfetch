"""Test the report command."""

# mypy: ignore-errors
# flake8: noqa

import argparse
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from dfetch.commands.report import Report, ReportTypes
from dfetch.util.license import LicenseScanResult
from tests.manifest_mock import mock_manifest

DEFAULT_ARGS = argparse.Namespace()
DEFAULT_ARGS.projects = []
DEFAULT_ARGS.type = ReportTypes.STDOUT
DEFAULT_ARGS.outfile = ""


@pytest.mark.parametrize(
    "name, projects",
    [
        ("empty", []),
        ("single_project", [{"name": "my_project"}]),
        ("two_projects", [{"name": "first"}, {"name": "second"}]),
    ],
)
def test_report(name, projects):
    report = Report()

    fake_superproject = Mock()
    fake_superproject.manifest = mock_manifest(projects)
    fake_superproject.root_directory = Path("/tmp")

    with patch(
        "dfetch.commands.report.create_super_project", return_value=fake_superproject
    ):
        with patch("dfetch.log.DLogger.print_info_line") as mocked_print_info_line:

            report(DEFAULT_ARGS)

            if projects:
                for project in projects:
                    mocked_print_info_line.assert_any_call(project["name"], "")
            else:
                mocked_print_info_line.assert_not_called()


# ---------------------------------------------------------------------------
# Report._determine_licenses – returns LicenseScanResult
# ---------------------------------------------------------------------------


def test_determine_licenses_not_fetched_returns_not_scanned(tmp_path):
    """When the destination doesn't exist, was_scanned must be False."""
    project = Mock()
    project.name = "my-project"
    project.destination = str(tmp_path / "nonexistent")

    with patch("dfetch.log.DLogger.print_warning_line"):
        result = Report._determine_licenses(project)

    assert isinstance(result, LicenseScanResult)
    assert result.was_scanned is False
    assert result.identified == []
    assert result.unclassified_files == []


def test_determine_licenses_empty_directory_returns_no_license_files(tmp_path):
    """A fetched directory with no license files should return an empty scan."""
    project_dir = tmp_path / "my-project"
    project_dir.mkdir()
    (project_dir / "README.md").write_text("# readme")

    project = Mock()
    project.name = "my-project"
    project.destination = str(project_dir)

    result = Report._determine_licenses(project)

    assert isinstance(result, LicenseScanResult)
    assert result.was_scanned is True
    assert result.identified == []
    assert result.unclassified_files == []


def test_determine_licenses_identified_license(tmp_path):
    """When a license is detected above threshold, it is in identified."""
    from dfetch.util.license import License

    project_dir = tmp_path / "my-project"
    project_dir.mkdir()
    license_file = project_dir / "LICENSE"
    license_file.write_text("MIT License\n\nPermission is hereby granted...")

    project = Mock()
    project.name = "my-project"
    project.destination = str(project_dir)

    fake_license = License(
        name="MIT License", spdx_id="MIT", trove_classifier=None, probability=0.99
    )

    with patch(
        "dfetch.commands.report.guess_license_in_file", return_value=fake_license
    ):
        result = Report._determine_licenses(project)

    assert result.was_scanned is True
    assert len(result.identified) == 1
    assert result.identified[0].spdx_id == "MIT"
    assert result.unclassified_files == []


def test_determine_licenses_below_threshold_is_unclassified(tmp_path):
    """License guesses below the threshold end up in unclassified_files."""
    from dfetch.util.license import License

    project_dir = tmp_path / "my-project"
    project_dir.mkdir()
    (project_dir / "LICENSE").write_text("Some ambiguous license text")

    project = Mock()
    project.name = "my-project"
    project.destination = str(project_dir)

    low_confidence_license = License(
        name="Unknown", spdx_id="MIT", trove_classifier=None, probability=0.50
    )

    with patch(
        "dfetch.commands.report.guess_license_in_file",
        return_value=low_confidence_license,
    ):
        with patch("dfetch.log.DLogger.print_warning_line"):
            result = Report._determine_licenses(project)

    assert result.was_scanned is True
    assert result.identified == []
    assert "LICENSE" in result.unclassified_files


def test_determine_licenses_none_result_is_unclassified(tmp_path):
    """When guess_license_in_file returns None, the file goes to unclassified."""
    project_dir = tmp_path / "my-project"
    project_dir.mkdir()
    (project_dir / "LICENSE").write_text("Can't classify this")

    project = Mock()
    project.name = "my-project"
    project.destination = str(project_dir)

    with patch("dfetch.commands.report.guess_license_in_file", return_value=None):
        with patch("dfetch.log.DLogger.print_warning_line"):
            result = Report._determine_licenses(project)

    assert result.was_scanned is True
    assert result.identified == []
    assert "LICENSE" in result.unclassified_files


def test_determine_licenses_result_includes_threshold(tmp_path):
    """The returned LicenseScanResult must embed the threshold value."""
    project_dir = tmp_path / "my-project"
    project_dir.mkdir()

    project = Mock()
    project.name = "my-project"
    project.destination = str(project_dir)

    result = Report._determine_licenses(project)

    # Threshold comes from LICENSE_PROBABILITY_THRESHOLD constant (0.80)
    assert result.threshold == pytest.approx(0.80)


def test_determine_licenses_threshold_boundary_at_exactly_080(tmp_path):
    """Probability exactly at 0.80 should be accepted (>= threshold)."""
    from dfetch.util.license import License

    project_dir = tmp_path / "my-project"
    project_dir.mkdir()
    (project_dir / "LICENSE").write_text("MIT License")

    project = Mock()
    project.name = "my-project"
    project.destination = str(project_dir)

    boundary_license = License(
        name="MIT License", spdx_id="MIT", trove_classifier=None, probability=0.80
    )

    with patch(
        "dfetch.commands.report.guess_license_in_file", return_value=boundary_license
    ):
        result = Report._determine_licenses(project)

    assert len(result.identified) == 1, "Probability exactly at threshold should be accepted"