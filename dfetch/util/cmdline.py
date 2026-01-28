"""Module for performing cmd line arguments."""

import logging
import os
import subprocess  # nosec
from collections.abc import Mapping
from typing import Any, Optional


class SubprocessCommandError(Exception):
    """Error raised when a subprocess fails.

    Whenever a subprocess is executed something can happen. This exception
    contains all the results for easier usage later on.
    """

    def __init__(
        self,
        cmd: Optional[list[str]] = None,
        stdout: str = "",
        stderr: str = "",
        returncode: int = 0,
    ):
        """Error."""
        cmd_str: str = " ".join(cmd or [])
        self._message = f">>>{cmd_str}<<< returned {returncode}:{os.linesep}{stderr}"
        self.cmd = cmd_str
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        super().__init__(self._message)

    @property
    def message(self) -> str:
        """Return the message of this SubprocessCommandError."""
        return self._message


def run_on_cmdline(
    logger: logging.Logger,
    cmd: list[str],
    env: Optional[Mapping[str, str]] = None,
) -> "subprocess.CompletedProcess[Any]":
    """Run a command and log the output, and raise if something goes wrong."""
    logger.debug(f"Running {cmd}")

    try:
        proc = subprocess.run(cmd, env=env, capture_output=True, check=True)  # nosec
    except subprocess.CalledProcessError as exc:
        raise SubprocessCommandError(
            exc.cmd,
            exc.output.decode().strip(),
            exc.stderr.decode().strip(),
            exc.returncode,
        ) from exc
    except FileNotFoundError as exc:
        raise RuntimeError(f"{cmd[0]} not available on system, please install") from exc

    stdout, stderr = proc.stdout, proc.stderr

    _log_output(proc, logger)

    if proc.returncode:
        raise SubprocessCommandError(
            cmd, stdout.decode(), stderr.decode().strip(), proc.returncode
        )

    return proc


def _log_output(proc: subprocess.CompletedProcess, logger: logging.Logger) -> None:  # type: ignore
    logger.debug(f"Return code: {proc.returncode}")

    _log_output_stream("stdout", proc.stdout, logger)
    _log_output_stream("stderr", proc.stderr, logger)


def _log_output_stream(name: str, stream: Any, logger: logging.Logger) -> None:
    logger.debug(f"{name}:")
    try:
        for line in stream.decode().split("\n\n"):
            logger.debug(line)
    except UnicodeDecodeError:
        for line in stream.decode(encoding="cp1252").split("\n\n"):
            logger.debug(line)
