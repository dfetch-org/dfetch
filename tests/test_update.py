"""Test the check command."""
# mypy: ignore-errors
# flake8: noqa

import argparse
from typing import Tuple
from unittest.mock import MagicMock, Mock, patch

import pytest

import dfetch
from dfetch.commands.update import Update
from dfetch.manifest.manifest import Manifest
from dfetch.manifest.project import ProjectEntry


def mock_manifest(name, projects):

    project_mocks = []

    for project in projects:
        mock_project = Mock(spec=ProjectEntry)
        mock_project.name = project['name']
        project_mocks += [mock_project]

    return MagicMock(spec=Manifest, projects=project_mocks)

@pytest.mark.parametrize('name, projects', [("empty", []),
                                            ("single_project", [{"name": "my_project"}]),
                                            ("two_projects", [{"name": "first"},{"name": "second"}])])
def test_update(name, projects):

    update = Update()

    with patch('dfetch.manifest.manifest.get_manifest') as mocked_get_manifest:
        with patch('dfetch.project.make') as mocked_make:

            mocked_get_manifest.return_value = (mock_manifest(name, projects), "/")

            update(argparse.Namespace)

            for project in projects:
                mocked_make.return_value.update.assert_called()
