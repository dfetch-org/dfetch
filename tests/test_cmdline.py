"""Test the cmdline."""
# mypy: ignore-errors
# flake8: noqa

import os
import subprocess
from subprocess import CalledProcessError, CompletedProcess
from unittest.mock import MagicMock, Mock, patch

import pytest

from dfetch.util.cmdline import SubprocessCommandError, run_on_cmdline

LS_CMD = "ls ."
LS_OK_RESULT = CompletedProcess(
    returncode=0, stdout="myfile".encode(), stderr="".encode(), args=LS_CMD
)
LS_NON_ZERO_RESULT = CalledProcessError(
    returncode=1, output="myfile".encode(), stderr="".encode(), cmd=LS_CMD
)
LS_NOK_RESULT = CalledProcessError(
    returncode=0, output="myfile".encode(), stderr="".encode(), cmd=LS_CMD
)
MISSING_CMD_RESULT = FileNotFoundError()


@pytest.mark.parametrize(
    "name, cmd, cmd_result, expectation",
    [
        ("cmd succeeds", LS_CMD, [LS_OK_RESULT], LS_OK_RESULT),
        ("cmd non-zero return", LS_CMD, [LS_NON_ZERO_RESULT], SubprocessCommandError),
        ("cmd raises", LS_CMD, [LS_NOK_RESULT], SubprocessCommandError),
        ("cmd missing", LS_CMD, [MISSING_CMD_RESULT], RuntimeError),
    ],
)
def test_run_on_cmdline(name, cmd, cmd_result, expectation):
    with patch("dfetch.util.cmdline.subprocess.run") as subprocess_mock:
        subprocess_mock.side_effect = cmd_result
        logger_mock = MagicMock()

        if isinstance(expectation, CompletedProcess):
            assert expectation == run_on_cmdline(logger_mock, cmd)
        else:
            with pytest.raises(expectation):
                run_on_cmdline(logger_mock, cmd)
