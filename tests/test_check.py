"""Test the check command."""
# mypy: ignore-errors
# flake8: noqa

import argparse
from typing import Tuple
from unittest.mock import MagicMock, Mock, patch

import pytest

from dfetch.commands.check import Check
from dfetch.manifest.project import ProjectEntry
from tests.manifest_mock import mock_manifest

DEFAULT_ARGS = argparse.Namespace(non_recursive=False)
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

                        mocked_get_manifest.return_value = (
                            mock_manifest(projects),
                            "/",
                        )
                        mocked_get_childmanifests.return_value = []

                        check(DEFAULT_ARGS)

                        for _ in projects:
                            mocked_make.return_value.check_for_update.assert_called()


@pytest.mark.parametrize(
    "name, projects",
    [
        ("empty", []),
        ("single_project", [{"name": "my_project"}]),
        ("two_projects", [{"name": "first"}, {"name": "second"}]),
    ],
)
def test_check_child_manifests(name, projects):

    parent = ProjectEntry({"name": "parent"})

    with patch(
        "dfetch.manifest.manifest.get_childmanifests"
    ) as mocked_get_childmanifests:
        with patch("dfetch.project.make") as mocked_make:

            mocked_get_childmanifests.return_value = [(mock_manifest(projects), "/")]

            Check._check_child_manifests(parent, "somepath")

            for _ in projects:
                mocked_make.return_value.check_for_update.assert_called()
