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

DEFAULT_ARGS = argparse.Namespace(non_recursive=False)
DEFAULT_ARGS.force = False


def mock_manifest(name, projects):

    project_mocks = []

    for project in projects:
        mock_project = Mock(spec=ProjectEntry)
        mock_project.name = project["name"]
        mock_project.destination = "some_dest"
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
def test_update(name, projects):

    update = Update()

    with patch("dfetch.manifest.manifest.get_manifest") as mocked_get_manifest:
        with patch(
            "dfetch.manifest.manifest.get_childmanifests"
        ) as mocked_get_childmanifests:
            with patch("dfetch.project.make") as mocked_make:
                with patch("os.path.exists"):
                    with patch("dfetch.commands.update.in_directory"):
                        mocked_get_manifest.return_value = (
                            mock_manifest(name, projects),
                            "/",
                        )
                        mocked_get_childmanifests.return_value = []

                        update(DEFAULT_ARGS)

                        for project in projects:
                            mocked_make.return_value.update.assert_called()


def test_forced_update():

    update = Update()

    with patch("dfetch.manifest.manifest.get_manifest") as mocked_get_manifest:
        mocked_get_manifest.return_value = (
            mock_manifest("MyProject", [{"name": "some_project"}]),
            "/",
        )
        with patch(
            "dfetch.manifest.manifest.get_childmanifests"
        ) as mocked_get_childmanifests:
            with patch("dfetch.project.make") as mocked_make:
                with patch("os.path.exists"):
                    with patch("dfetch.commands.update.in_directory"):
                        mocked_get_childmanifests.return_value = []

                        args = DEFAULT_ARGS
                        args.force = True

                        update(args)
                        mocked_make.return_value.update.assert_called_once_with(
                            force=True
                        )


def test_create_menu():

    subparsers = argparse.ArgumentParser().add_subparsers()

    Update.create_menu(subparsers)

    assert "update" in subparsers.choices

    options = [
        ["-h", "--help"],
        ["-N", "--non-recursive"],
        ["-f", "--force"],
    ]

    for action, expected_options in zip(subparsers.choices["update"]._actions, options):
        assert action.option_strings == expected_options
