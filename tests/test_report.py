"""Test the report command."""

# mypy: ignore-errors
# flake8: noqa

import argparse
import os
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call

import pytest

from dfetch.commands.report import Report, ReportTypes, LICENSE_PROBABILITY_THRESHOLD
from dfetch.manifest.project import ProjectEntry
from dfetch.util.license import License, LicenseScanResult
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
# Report._determine_licenses – LicenseScanResult return values
# ---------------------------------------------------------------------------


def _make_project_entry(name: str = "my-project", destination: str = "/some/path") -> Mock:
    p = Mock(spec=ProjectEntry)
    p.name = name
    p.destination = destination
    return p


def test_determine_licenses_returns_not_scanned_when_destination_missing():
    """Returns LicenseScanResult(was_scanned=False) when project destination doesn't exist."""
    project = _make_project_entry(destination="/nonexistent/path")
    with patch("os.path.exists", return_value=False):
        result = Report._determine_licenses(project)
    assert isinstance(result, LicenseScanResult)
    assert result.was_scanned is False
    assert result.identified == []
    assert result.unclassified_files == []


def test_determine_licenses_returns_scanned_true_when_destination_exists(tmp_path):
    """Returns was_scanned=True when destination exists."""
    dest = tmp_path / "proj"
    dest.mkdir()
    project = _make_project_entry(destination=str(dest))

    with patch("dfetch.util.license.infer_license.api.probabilities", return_value=[]):
        result = Report._determine_licenses(project)

    assert result.was_scanned is True


def test_determine_licenses_sets_threshold(tmp_path):
    """Returned LicenseScanResult.threshold matches LICENSE_PROBABILITY_THRESHOLD."""
    dest = tmp_path / "proj"
    dest.mkdir()
    project = _make_project_entry(destination=str(dest))

    with patch("dfetch.util.license.infer_license.api.probabilities", return_value=[]):
        result = Report._determine_licenses(project)

    assert result.threshold == LICENSE_PROBABILITY_THRESHOLD


def test_determine_licenses_identifies_license_above_threshold(tmp_path):
    """A license file whose probability >= threshold ends up in identified."""
    dest = tmp_path / "proj"
    dest.mkdir()
    (dest / "LICENSE").write_text("MIT License\nCopyright 2024", encoding="utf-8")
    project = _make_project_entry(destination=str(dest))

    mock_inferred = MagicMock()
    mock_inferred.name = "MIT License"
    mock_inferred.shortname = "MIT"
    mock_inferred.trove_classifier = None

    with patch(
        "dfetch.util.license.infer_license.api.probabilities",
        return_value=[(mock_inferred, LICENSE_PROBABILITY_THRESHOLD)],
    ):
        result = Report._determine_licenses(project)

    assert len(result.identified) == 1
    assert result.identified[0].spdx_id == "MIT"
    assert result.unclassified_files == []


def test_determine_licenses_rejects_license_below_threshold(tmp_path):
    """A license file whose probability < threshold ends up in unclassified_files."""
    dest = tmp_path / "proj"
    dest.mkdir()
    (dest / "LICENSE").write_text("Some vague text", encoding="utf-8")
    project = _make_project_entry(destination=str(dest))

    mock_inferred = MagicMock()
    mock_inferred.name = "MIT License"
    mock_inferred.shortname = "MIT"
    mock_inferred.trove_classifier = None

    with patch(
        "dfetch.util.license.infer_license.api.probabilities",
        return_value=[(mock_inferred, LICENSE_PROBABILITY_THRESHOLD - 0.01)],
    ):
        result = Report._determine_licenses(project)

    assert result.identified == []
    assert "LICENSE" in result.unclassified_files


def test_determine_licenses_no_license_file(tmp_path):
    """When no license file exists, both identified and unclassified_files are empty."""
    dest = tmp_path / "proj"
    dest.mkdir()
    (dest / "README.md").write_text("# My Project", encoding="utf-8")
    project = _make_project_entry(destination=str(dest))

    result = Report._determine_licenses(project)

    assert result.was_scanned is True
    assert result.identified == []
    assert result.unclassified_files == []


def test_determine_licenses_unclassifiable_file_no_probabilities(tmp_path):
    """When infer_license returns nothing, the file goes to unclassified_files."""
    dest = tmp_path / "proj"
    dest.mkdir()
    (dest / "LICENSE").write_text("No recognizable license text here", encoding="utf-8")
    project = _make_project_entry(destination=str(dest))

    with patch(
        "dfetch.util.license.infer_license.api.probabilities",
        return_value=[],
    ):
        result = Report._determine_licenses(project)

    assert result.identified == []
    assert "LICENSE" in result.unclassified_files


def test_determine_licenses_threshold_boundary_exact_match(tmp_path):
    """A probability exactly equal to the threshold is accepted (>= not >)."""
    dest = tmp_path / "proj"
    dest.mkdir()
    (dest / "LICENSE").write_text("MIT License text", encoding="utf-8")
    project = _make_project_entry(destination=str(dest))

    mock_inferred = MagicMock()
    mock_inferred.name = "MIT License"
    mock_inferred.shortname = "MIT"
    mock_inferred.trove_classifier = None

    # Exactly at threshold: should be identified, not rejected
    with patch(
        "dfetch.util.license.infer_license.api.probabilities",
        return_value=[(mock_inferred, 0.80)],
    ):
        result = Report._determine_licenses(project)

    assert len(result.identified) == 1
    assert result.unclassified_files == []