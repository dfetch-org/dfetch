"""Test the list command."""
# mypy: ignore-errors
# flake8: noqa

import argparse
from typing import Tuple
from unittest.mock import MagicMock, Mock, patch

import pytest

import dfetch
from dfetch.commands.list import List
from dfetch.manifest.manifest import Manifest
from dfetch.manifest.project import ProjectEntry


def mock_manifest(projects):

    project_mocks = []

    for project in projects:
        mock_project = Mock(spec=ProjectEntry)
        mock_project.name = project["name"]
        project_mocks += [mock_project]

    return MagicMock(spec=Manifest, projects=project_mocks)


@pytest.mark.parametrize(
    "name, projects",
    [
        ("empty", []),
        ("single_project", [{"name": "my_project"}]),
        ("two_projects", [{"name": "first"}, {"name": "second"}]),
    ],
)
def test_list(name, projects):

    list = List()

    with patch("dfetch.manifest.manifest.get_manifest") as mocked_get_manifest:
        with patch("dfetch.log.DLogger.print_info_line") as mocked_print_info_line:

            mocked_get_manifest.return_value = (mock_manifest(projects), "/")

            list(argparse.Namespace)

            if projects:
                for project in projects:
                    mocked_print_info_line.assert_any_call("project", project["name"])
            else:
                mocked_print_info_line.assert_not_called()
