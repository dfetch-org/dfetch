"""Module for performing cmd line arguments."""

import logging
import os
import subprocess  # nosec
from typing import Any  # pylint: disable=unused-import


class SubprocessCommandError(Exception):
    """Error raised when a subprocess fails.

    Whenever a subprocess is executed something can happen. This exception
    contains all the results for easier usage later on.
    """

    def __init__(self, cmd: str, stdout: str, stderr: str, returncode: int):
        """Error."""
        self._message = f"{cmd} returned {returncode}:{os.linesep}{stderr}"
        self.cmd = cmd
        self.stderr = stdout
        self.stdout = stderr
        self.returncode = returncode
        super().__init__(self._message)

    @property
    def message(self) -> str:
        """Return the message of this SubprocessCommandError."""
        return self._message


def run_on_cmdline(
    logger: logging.Logger, cmd: str
) -> "subprocess.CompletedProcess[Any]":
    """Run a command and log the output, and raise if something goes wrong."""
    logger.debug(f"Running {cmd}")

    try:
        proc = subprocess.run(  # nosec
            cmd.split(" "), stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
        )
    except subprocess.CalledProcessError as exc:
        raise SubprocessCommandError(
            exc.cmd,
            exc.output.decode().strip(),
            exc.stderr.decode().strip(),
            exc.returncode,
        ) from exc
    except FileNotFoundError as exc:
        cmd = cmd.split(" ")[0]
        raise RuntimeError(f"{cmd} not available on system, please install") from exc

    stdout, stderr = proc.stdout, proc.stderr

    logger.debug(f"Return code: {proc.returncode}")

    logger.debug("stdout:")
    for line in stdout.decode().split("\n\n"):
        logger.debug(line)

    logger.debug("stderr:")
    for line in stderr.decode().split("\n\n"):
        logger.debug(line)

    if proc.returncode:
        raise SubprocessCommandError(
            cmd, stdout.decode(), stderr.decode().strip(), proc.returncode
        )

    return proc
