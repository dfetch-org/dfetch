"""Test the report command."""

# mypy: ignore-errors
# flake8: noqa

import argparse
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from dfetch.commands.report import LICENSE_PROBABILITY_THRESHOLD, Report, ReportTypes
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
# _determine_licenses — returns LicenseScanResult (changed in this PR)
# ---------------------------------------------------------------------------


def _make_project_entry(name: str, destination: str) -> Mock:
    p = Mock()
    p.name = name
    p.destination = destination
    return p


class TestDetermineLicenses:
    """Report._determine_licenses must return LicenseScanResult in all cases."""

    def test_returns_license_scan_result_instance(self, tmp_path):
        project_dir = tmp_path / "myproject"
        project_dir.mkdir()
        project = _make_project_entry("myproject", str(project_dir))

        with patch("dfetch.commands.report.glob.glob", return_value=[]):
            result = Report._determine_licenses(project)

        assert isinstance(result, LicenseScanResult)

    def test_not_fetched_returns_was_scanned_false(self, tmp_path):
        project = _make_project_entry("missing", str(tmp_path / "nonexistent"))
        result = Report._determine_licenses(project)
        assert result.was_scanned is False
        assert result.identified == []

    def test_scanned_with_no_license_files_returns_empty(self, tmp_path):
        project_dir = tmp_path / "nofiles"
        project_dir.mkdir()
        project = _make_project_entry("nofiles", str(project_dir))

        with patch("dfetch.commands.report.glob.glob", return_value=[]):
            result = Report._determine_licenses(project)

        assert result.was_scanned is True
        assert result.identified == []
        assert result.unclassified_files == []

    def test_threshold_stored_in_result(self, tmp_path):
        project_dir = tmp_path / "withfiles"
        project_dir.mkdir()
        project = _make_project_entry("withfiles", str(project_dir))

        with patch("dfetch.commands.report.glob.glob", return_value=[]):
            result = Report._determine_licenses(project)

        assert result.threshold == LICENSE_PROBABILITY_THRESHOLD

    def test_identified_license_included_at_exactly_threshold(self, tmp_path):
        """Probability exactly equal to threshold must be accepted (>= not >)."""
        project_dir = tmp_path / "atthreshold"
        project_dir.mkdir()
        (project_dir / "LICENSE").write_text("MIT text")
        project = _make_project_entry("atthreshold", str(project_dir))

        guessed = Mock()
        guessed.probability = LICENSE_PROBABILITY_THRESHOLD  # exactly 0.80

        with patch("dfetch.commands.report.glob.glob", return_value=["LICENSE"]):
            with patch("dfetch.commands.report.is_license_file", return_value=True):
                with patch(
                    "dfetch.commands.report.guess_license_in_file", return_value=guessed
                ):
                    result = Report._determine_licenses(project)

        assert guessed in result.identified
        assert "LICENSE" not in result.unclassified_files

    def test_license_below_threshold_goes_to_unclassified(self, tmp_path):
        project_dir = tmp_path / "below"
        project_dir.mkdir()
        (project_dir / "LICENSE").write_text("random text")
        project = _make_project_entry("below", str(project_dir))

        guessed = Mock()
        guessed.probability = LICENSE_PROBABILITY_THRESHOLD - 0.01  # just below

        with patch("dfetch.commands.report.glob.glob", return_value=["LICENSE"]):
            with patch("dfetch.commands.report.is_license_file", return_value=True):
                with patch(
                    "dfetch.commands.report.guess_license_in_file", return_value=guessed
                ):
                    result = Report._determine_licenses(project)

        assert result.identified == []
        assert "LICENSE" in result.unclassified_files

    def test_unguessable_license_goes_to_unclassified(self, tmp_path):
        """When guess_license_in_file returns None the file is unclassified."""
        project_dir = tmp_path / "unguessable"
        project_dir.mkdir()
        (project_dir / "LICENSE").write_text("gibberish")
        project = _make_project_entry("unguessable", str(project_dir))

        with patch("dfetch.commands.report.glob.glob", return_value=["LICENSE"]):
            with patch("dfetch.commands.report.is_license_file", return_value=True):
                with patch(
                    "dfetch.commands.report.guess_license_in_file", return_value=None
                ):
                    result = Report._determine_licenses(project)

        assert result.identified == []
        assert "LICENSE" in result.unclassified_files

    def test_multiple_files_partitioned_correctly(self, tmp_path):
        """Multiple license files: some identified, some unclassified."""
        project_dir = tmp_path / "multifile"
        project_dir.mkdir()
        project = _make_project_entry("multifile", str(project_dir))

        good_guess = Mock()
        good_guess.probability = 0.95

        bad_guess = Mock()
        bad_guess.probability = 0.50

        file_to_guess = {
            "LICENSE": good_guess,
            "COPYING": bad_guess,
        }

        with patch("dfetch.commands.report.glob.glob", return_value=["LICENSE", "COPYING"]):
            with patch("dfetch.commands.report.is_license_file", return_value=True):
                with patch(
                    "dfetch.commands.report.guess_license_in_file",
                    side_effect=lambda f: file_to_guess[f],
                ):
                    result = Report._determine_licenses(project)

        assert good_guess in result.identified
        assert bad_guess not in result.identified
        assert "COPYING" in result.unclassified_files
        assert "LICENSE" not in result.unclassified_files


# ---------------------------------------------------------------------------
# LICENSE_PROBABILITY_THRESHOLD value
# ---------------------------------------------------------------------------


def test_license_probability_threshold_value():
    """Threshold must be 0.80 as documented."""
    assert LICENSE_PROBABILITY_THRESHOLD == 0.80