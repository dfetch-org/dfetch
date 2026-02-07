"""Test the report command."""

# mypy: ignore-errors
# flake8: noqa

import argparse
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from dfetch.commands.report import Report, ReportTypes
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
        with patch("dfetch.log.DLogger.print_report_line") as mocked_print_report_line:

            report(DEFAULT_ARGS)

            if projects:
                for project in projects:
                    mocked_print_report_line.assert_any_call("project", project["name"])
            else:
                mocked_print_report_line.assert_not_called()
