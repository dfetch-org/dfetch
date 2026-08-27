"""Module for performing cmd line arguments."""

import logging
import os
import subprocess  # nosec
from collections.abc import Mapping
from typing import Any


class SubprocessCommandError(Exception):
    """Error raised when a subprocess fails.

    Whenever a subprocess is executed something can happen. This exception
    contains all the results for easier usage later on.
    """

    def __init__(
        self,
        cmd: list[str] | None = None,
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


def decode_subprocess_output(data: bytes) -> str:
    """Decode bytes from a subprocess, tolerating non-UTF-8 output.

    Command line tools such as ``svn`` can emit output in the system's
    native code page (e.g. CP1252 on Windows) rather than UTF-8, for
    example when a file path contains accented characters. UTF-8 is tried
    first since it is the common case, then CP1252, a common source of
    non-UTF-8 output. As a last resort, undecodable bytes are replaced so
    that unexpected output never crashes the command that produced it.
    """
    try:
        return data.decode()
    except UnicodeDecodeError:
        pass
    return data.decode(encoding="cp1252", errors="replace")


def run_on_cmdline(
    logger: logging.Logger,
    cmd: list[str],
    env: Mapping[str, str] | None = None,
    input_data: bytes | None = None,
) -> "subprocess.CompletedProcess[Any]":
    """Run a command and log the output, and raise if something goes wrong."""
    logger.debug(f"Running {cmd}")

    try:
        proc = subprocess.run(  # nosec B603 — shell=False, list-form args from internal code
            cmd, shell=False, env=env, input=input_data, capture_output=True, check=True
        )
    except subprocess.CalledProcessError as exc:
        raise SubprocessCommandError(
            exc.cmd,
            decode_subprocess_output(exc.output).strip(),
            decode_subprocess_output(exc.stderr).strip(),
            exc.returncode,
        ) from exc
    except FileNotFoundError as exc:
        raise RuntimeError(f"{cmd[0]} not available on system, please install") from exc

    stdout, stderr = proc.stdout, proc.stderr

    _log_output(proc, logger)

    if proc.returncode:
        raise SubprocessCommandError(
            cmd,
            decode_subprocess_output(stdout),
            decode_subprocess_output(stderr).strip(),
            proc.returncode,
        )

    return proc


def _log_output(proc: subprocess.CompletedProcess, logger: logging.Logger) -> None:  # type: ignore
    logger.debug(f"Return code: {proc.returncode}")

    _log_output_stream("stdout", proc.stdout, logger)
    _log_output_stream("stderr", proc.stderr, logger)


def _log_output_stream(name: str, stream: Any, logger: logging.Logger) -> None:
    logger.debug(f"{name}:")
    for line in decode_subprocess_output(stream).split("\n\n"):
        logger.debug(line)
