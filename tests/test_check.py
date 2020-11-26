"""Test the check command."""
# mypy: ignore-errors
# flake8: noqa

import argparse
from typing import Tuple
from unittest.mock import MagicMock, Mock, patch

import pytest

import dfetch
from dfetch.commands.check import Check
from dfetch.manifest.manifest import Manifest
from dfetch.manifest.project import ProjectEntry


@pytest.fixture(ids=["empty", "single_project", "two_projects"],
               params=[[], [{"name": "my_project"}], [{"name": "first"},{"name": "second"}]])
def get_manifest(monkeypatch, request):
    """Get empty manifest."""


    projects = []

    for project in request.param:
        mock_project = Mock(spec=ProjectEntry)
        mock_project.name = project['name']
        projects += [mock_project]

    mocked_manifest = MagicMock(spec=Manifest, projects=projects)

    def mocked_get_manifest() -> Tuple[Manifest, str]:
        return (mocked_manifest, "/")

    monkeypatch.setattr(dfetch.manifest.manifest, "get_manifest", mocked_get_manifest)


def test_check(get_manifest):

    check = Check()

    with patch('dfetch.project.make'):
        check(argparse.Namespace)
