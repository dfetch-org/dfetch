"""Test the check command."""
# mypy: ignore-errors
# flake8: noqa

import argparse
from unittest.mock import patch

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

    with patch("dfetch.manifest.manifest.get_manifest") as mocked_get_manifest:
        with patch(
            "dfetch.manifest.manifest.get_childmanifests"
        ) as mocked_get_childmanifests:
            with patch("dfetch.project.make") as mocked_make:
                with patch("os.path.exists"):
                    with patch("dfetch.commands.check.in_directory"):
                        with patch("dfetch.commands.check.CheckStdoutReporter"):
                            mocked_get_manifest.return_value = (
                                mock_manifest(projects),
                                "/",
                            )
                            mocked_get_childmanifests.return_value = []

                            check(DEFAULT_ARGS)

                            for _ in projects:
                                mocked_make.return_value.check_for_update.assert_called()
