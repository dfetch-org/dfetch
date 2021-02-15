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

    check = List()

    with patch("dfetch.manifest.manifest.get_manifest") as mocked_get_manifest:
        with patch("dfetch.project.make") as mocked_make:

            mocked_get_manifest.return_value = (mock_manifest(projects), "/")

            check(argparse.Namespace)

            for project in projects:
                mocked_make.return_value.remote.assert_called()

def test_log_metadata():

    list_cmd = List()
    with patch("dfetch.manifest.manifest.get_manifest") as mocked_get_manifest:
        mocked_get_manifest.return_value = (mock_manifest([{"name": "myproject"}]), "/")
        with patch("dfetch.commands.list.Metadata") as mocked_metadata:
            mocked_metadata.from_file.side_effect = FileNotFoundError
            args = MagicMock()
            args.project = None

            with pytest.raises(FileNotFoundError):
                list_cmd(args)
