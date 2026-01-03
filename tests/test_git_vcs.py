"""Test the git."""

# mypy: ignore-errors
# flake8: noqa

import os
from subprocess import CompletedProcess
from unittest.mock import Mock, patch

import pytest

from dfetch.util.cmdline import SubprocessCommandError
from dfetch.vcs.git import (
    GitLocalRepo,
    GitRemote,
    _build_git_ssh_command,
)


@pytest.mark.parametrize(
    "name, cmd_result, expectation",
    [
        ("git repo", [CompletedProcess(args=[], returncode=0, stdout="Yep!")], True),
        ("not a git repo", [SubprocessCommandError()], False),
        ("no git", [RuntimeError()], False),
        ("somewhere.git", [], True),
    ],
)
def test_remote_check(name, cmd_result, expectation):

    os.environ["GIT_SSH_COMMAND"] = "ssh"  # prevents additional subprocess call

    with patch("dfetch.vcs.git.run_on_cmdline") as run_on_cmdline_mock:
        run_on_cmdline_mock.side_effect = cmd_result

        assert GitRemote(name).is_git() == expectation


@pytest.mark.parametrize(
    "name, project, cmd_result, expectation",
    [
        ("SSH url", "sshProject", [1], True),
        (
            "http url",
            "httpProject",
            ["Yep!"],
            True,
        ),
        (
            "Failed command",
            "proj1",
            [SubprocessCommandError()],
            False,
        ),
        (
            "No git",
            "proj2",
            [RuntimeError()],
            False,
        ),
    ],
)
def test_check(name, project, cmd_result, expectation):
    with patch("dfetch.vcs.git.run_on_cmdline") as run_on_cmdline_mock:
        with patch("dfetch.vcs.git.in_directory"):
            run_on_cmdline_mock.side_effect = cmd_result

            assert GitLocalRepo(project).is_git() == expectation


TRIMMED_LSREMOTE_CPPUTEST = """
32ee13a803de50d057653588a9bdb61e2db5a6eb	refs/heads/gh-pages
33d11e10699bae03ba2a58a280e92494f4fa0d82	refs/heads/master
f4c3a8517eae810a1057f954029d2aff9a901cae	refs/heads/separate_gtest
0e3b216c7ab365b67765e94aeb45085c4db029e0	refs/tags/3.7.2
d3a34ab2d012e23e0ce1fbe9ca8a399fdf49a4b9	refs/tags/latest-passing-build
33d11e10699bae03ba2a58a280e92494f4fa0d82	refs/tags/latest-passing-build^{}
5b4ecb474a7c7260933cb7f0b43bb173ef72ed06	refs/tags/v3.3
4751ae217904fb9e4767a5b40e0b71f3dd1cec80	refs/tags/v3.3^{}
542036ed8cb3e57510f7e1d758a96964825fd7c7	refs/tags/v3.4
b81fc3a10f5e69ecca767625f88f6b90e5b84119	refs/tags/v3.4^{}
ee14dc0646250d601a1d7f4f8f06ec142e65917b	refs/tags/v3.5
2139e96793f736102f9e4c465a20f8a72daab0a0	refs/tags/v3.6
bb134f7540165031f3fae8182634f5f64979356a	refs/tags/v3.7
c8d11d68ba341de535592533599dd437b2e25f3b	refs/tags/v3.7.1
e25097614e1c4856036366877a02346c4b36bb5b	refs/tags/v3.8
b9b841c56c524a10ccd40e88c3acaf9d5ec751c2	refs/tags/v4.0
67d2dfd41e13f09ff218aa08e2d35f1c32f032a1	refs/tags/v4.0^{}
"""


def test_ls_remote():
    with patch("dfetch.vcs.git.run_on_cmdline") as run_on_cmdline_mock:
        run_on_cmdline_mock.return_value.stdout = TRIMMED_LSREMOTE_CPPUTEST.encode(
            "UTF-8"
        )

        info = GitRemote._ls_remote("some-url")

        expected = {
            "refs/heads/gh-pages": "32ee13a803de50d057653588a9bdb61e2db5a6eb",
            "refs/heads/master": "33d11e10699bae03ba2a58a280e92494f4fa0d82",
            "refs/heads/separate_gtest": "f4c3a8517eae810a1057f954029d2aff9a901cae",
            "refs/tags/3.7.2": "0e3b216c7ab365b67765e94aeb45085c4db029e0",
            "refs/tags/latest-passing-build": "33d11e10699bae03ba2a58a280e92494f4fa0d82",
            "refs/tags/v3.3": "4751ae217904fb9e4767a5b40e0b71f3dd1cec80",
            "refs/tags/v3.4": "b81fc3a10f5e69ecca767625f88f6b90e5b84119",
            "refs/tags/v3.5": "ee14dc0646250d601a1d7f4f8f06ec142e65917b",
            "refs/tags/v3.6": "2139e96793f736102f9e4c465a20f8a72daab0a0",
            "refs/tags/v3.7": "bb134f7540165031f3fae8182634f5f64979356a",
            "refs/tags/v3.7.1": "c8d11d68ba341de535592533599dd437b2e25f3b",
            "refs/tags/v3.8": "e25097614e1c4856036366877a02346c4b36bb5b",
            "refs/tags/v4.0": "67d2dfd41e13f09ff218aa08e2d35f1c32f032a1",
        }

        assert info == expected


@pytest.mark.parametrize(
    "name, env_ssh, git_config_ssh, expected",
    [
        (
            "env var present",
            "ssh -i keyfile",
            None,
            "ssh -i keyfile -o BatchMode=yes",
        ),
        (
            "git config",
            None,
            "ssh -F configfile",
            "ssh -F configfile -o BatchMode=yes",
        ),
        ("no env or git config", None, None, "ssh -o BatchMode=yes"),
        (
            "env with batchmode",
            "ssh -o BatchMode=yes",
            None,
            "ssh -o BatchMode=yes",
        ),
    ],
)
def test_build_git_ssh_command(name, env_ssh, git_config_ssh, expected):

    with patch.dict(
        os.environ, {"GIT_SSH_COMMAND": env_ssh} if env_ssh else {}, clear=True
    ):
        mock_run_git_config = Mock()
        if git_config_ssh is not None:
            mock_run_git_config.return_value.stdout = git_config_ssh.encode()
        else:
            mock_run_git_config.side_effect = SubprocessCommandError()

        with patch("dfetch.vcs.git.run_on_cmdline", mock_run_git_config):
            with patch("dfetch.vcs.git.logger") as mock_logger:
                result = _build_git_ssh_command()
                assert result == expected

                if "BatchMode=" in (env_ssh or git_config_ssh or ""):
                    mock_logger.debug.assert_called_once()
                else:
                    mock_logger.debug.assert_not_called()
