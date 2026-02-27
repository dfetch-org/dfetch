"""Test the check command."""

# mypy: ignore-errors
# flake8: noqa

import argparse
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from dfetch.commands.check import Check
from tests.manifest_mock import mock_manifest

DEFAULT_ARGS = argparse.Namespace(
    no_recommendations=False, jenkins_json=None, sarif=None, code_climate=None
)
DEFAULT_ARGS.projects = []


@pytest.mark.parametrize(
    "name, projects",
    [
        ("empty", []),
        ("single_project", [{"name": "my_project"}]),
        ("two_projects", [{"name": "first"}, {"name": "second"}]),
    ],
)
def test_check(name, projects):
    check = Check()

    fake_superproject = Mock()
    fake_superproject.manifest = mock_manifest(projects)
    fake_superproject.root_directory = Path("/tmp")

    with patch(
        "dfetch.commands.check.create_super_project", return_value=fake_superproject
    ):
        with patch("dfetch.manifest.parse.get_submanifests") as mocked_get_submanifests:
            with patch("dfetch.project.create_sub_project") as mocked_create:
                with patch("os.path.exists"):
                    with patch("dfetch.commands.check.in_directory"):
                        with patch("dfetch.commands.check.CheckStdoutReporter"):
                            mocked_get_submanifests.return_value = []

                            check(DEFAULT_ARGS)

                            for _ in projects:
                                mocked_create.return_value.check_for_update.assert_called()
