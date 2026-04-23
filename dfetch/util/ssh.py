"""SSH command allowlist validation."""

import os
import re
import shlex

_SAFE_SSH_OPTION_KEYS = frozenset(
    {"StrictHostKeyChecking", "BatchMode", "UserKnownHostsFile"}
)

_PORT_RE = re.compile(r"^[0-9]{1,5}$")


class InvalidSshCommandError(Exception):
    """Raised when an SSH command string does not pass the allowlist."""


def _validate_value_flag(tokens: list[str], i: int, flag: str) -> None:
    """Raise InvalidSshCommandError if a -i or -p flag or its value is invalid."""
    if i + 1 >= len(tokens):
        raise InvalidSshCommandError(f"flag {flag!r} requires a value")
    if flag == "-p" and not _PORT_RE.match(tokens[i + 1]):
        raise InvalidSshCommandError("-p requires a numeric port")


def _validate_option_flag(tokens: list[str], i: int) -> None:
    """Raise InvalidSshCommandError if a -o flag or its value is invalid."""
    if i + 1 >= len(tokens):
        raise InvalidSshCommandError("-o requires a value")
    key = tokens[i + 1].split("=", 1)[0]
    if key not in _SAFE_SSH_OPTION_KEYS:
        raise InvalidSshCommandError(
            f"SSH option {tokens[i + 1]!r} is not in the allowed list"
        )


def _validate_ssh_flags(tokens: list[str]) -> None:
    """Raise InvalidSshCommandError if any flag token after the binary is invalid."""
    i = 1
    while i < len(tokens):
        flag = tokens[i]
        if flag in ("-i", "-p"):
            _validate_value_flag(tokens, i, flag)
            i += 2
        elif flag == "-o":
            _validate_option_flag(tokens, i)
            i += 2
        else:
            raise InvalidSshCommandError(f"flag {flag!r} is not allowed")


def sanitize_ssh_cmd(ssh_cmd: str) -> str:
    """Return *ssh_cmd* if it passes the allowlist; raise :exc:`InvalidSshCommandError` otherwise.

    Accepts:
    * A bare absolute path to an ssh binary (no arguments).
    * ``ssh`` with a restricted set of flags: ``-i <file>``, ``-p <port>``,
      ``-o`` with option key in :data:`_SAFE_SSH_OPTION_KEYS`.
    """
    try:
        tokens = shlex.split(ssh_cmd)
    except ValueError as exc:
        raise InvalidSshCommandError("cannot parse ssh command") from exc

    if not tokens:
        raise InvalidSshCommandError("empty ssh command")

    binary = tokens[0]

    if os.path.isabs(binary):
        if len(tokens) == 1:
            return ssh_cmd
        raise InvalidSshCommandError("absolute-path ssh binary may not carry arguments")

    if binary != "ssh":
        raise InvalidSshCommandError("ssh command must be 'ssh' or an absolute path")

    _validate_ssh_flags(tokens)
    return shlex.join(tokens)
