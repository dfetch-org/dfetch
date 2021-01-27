"""Test the git."""
# mypy: ignore-errors
# flake8: noqa

import os
from unittest.mock import MagicMock, patch

import pytest

from dfetch.manifest.project import ProjectEntry
from dfetch.project.git import GitRepo
from dfetch.util.cmdline import SubprocessCommandError


@pytest.mark.parametrize(
    "name, cmd_result, expectation",
    [
        ("git repo", ["Yep!"], True),
        ("not a git repo", [SubprocessCommandError()], False),
        ("no git", [RuntimeError()], False),
    ],
)
def test_check_path(name, cmd_result, expectation):

    with patch("dfetch.project.git.run_on_cmdline") as run_on_cmdline_mock:

        run_on_cmdline_mock.side_effect = cmd_result

        assert GitRepo.check_path() == expectation


@pytest.mark.parametrize(
    "name, project, cmd_result, expectation",
    [
        ("SSH url", ProjectEntry({'name': "sshProject", 'url':"some.git"}), [], True),
        ("http url", ProjectEntry({'name': "httpProject", 'url':"some/bla"}), ["Yep!"], True),
        ("Failed command", ProjectEntry({'name': "proj1", 'url':"some/bla"}), [SubprocessCommandError()], False),
        ("No git", ProjectEntry({'name': "proj2", 'url':"some/bla"}), [RuntimeError()], False),
    ],
)
def test_check(name, project, cmd_result, expectation):

    with patch("dfetch.project.git.run_on_cmdline") as run_on_cmdline_mock:

        run_on_cmdline_mock.side_effect = cmd_result

        assert GitRepo(project).check() == expectation
