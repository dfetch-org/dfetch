"""Test the report command."""
# mypy: ignore-errors
# flake8: noqa

import argparse
from unittest.mock import patch

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

    with patch("dfetch.manifest.manifest.get_manifest") as mocked_get_manifest:
        with patch("dfetch.log.DLogger.print_info_line") as mocked_print_info_line:
            mocked_get_manifest.return_value = (mock_manifest(projects), "/")

            report(DEFAULT_ARGS)

            if projects:
                for project in projects:
                    mocked_print_info_line.assert_any_call("project", project["name"])
            else:
                mocked_print_info_line.assert_not_called()
