#!/usr/bin/env python3
"""Drive an interactive dfetch command through a real pty for asciinema recordings.

Usage::

    python3 interactive_helper.py <dfetch-args...> < keystrokes.txt

Interactive dfetch commands (like ``add -i``) use a real interactive-terminal
UI -- ghost-text prompts, hierarchical tree browsers -- that reads raw
keypresses straight from the terminal, so there is nothing to mock at the
Python level; the only way to automate a recording of one is to actually
drive a terminal.

This script spawns ``dfetch`` inside its own pty (via ``pexpect``) and feeds
it a keystroke script read from stdin, one scripted input per line::

    [WAIT "<regex>"] SEND <keys> DELAY <seconds> [REPEAT <count>]

- ``WAIT "<regex>"`` (optional) waits for ``<regex>`` to appear in the
  child's output before sending; omit it to send right after the previous
  line's delay (e.g. repeated Down-presses while stepping through a tree).
- ``<keys>`` is ``ENTER``, ``UP``, ``DOWN``, ``LEFT``, ``RIGHT``, or
  ``SPACE`` (resolved to their terminal escape sequences), or a quoted
  literal sent as-is, with ``\\r``/``\\n``/``\\t`` recognised (e.g.
  ``"y\\r"``).
- ``DELAY <seconds>`` is how long to pause -- draining and mirroring output
  the whole time -- before sending, to simulate human timing.
- ``REPEAT <count>`` (optional, default 1) repeats the line *count* times;
  only the first repetition waits on ``WAIT``.

Blank lines and lines starting with ``#`` are ignored. Everything the inner
pty prints is mirrored to this script's own stdout as it arrives, so when
this script is itself run under ``asciinema rec -c``, the recorder captures
dfetch's real terminal output with real timing -- and no human needs to be
at the keyboard.

This script has no knowledge of any particular dfetch command; the demo
script piping keystrokes in on stdin owns that.
"""

from __future__ import annotations

import dataclasses
import os
import shlex
import sys
import time

import pexpect

_PUMP_SLICE = 0.02  # granularity for draining/mirroring output while paused

_KEY_ALIASES = {
    "ENTER": "\r",
    "UP": "\x1b[A",
    "DOWN": "\x1b[B",
    "RIGHT": "\x1b[C",
    "LEFT": "\x1b[D",
    "SPACE": " ",
}


@dataclasses.dataclass(frozen=True)
class Keystroke:
    """One scripted input to send to the driven dfetch process.

    *expect* is a regex to wait for before sending *keys* (``None`` to send
    right after the previous keystroke's delay). *delay* is how long to
    pause -- draining and mirroring output the whole time -- before sending.
    """

    expect: str | None
    keys: str
    delay: float


def _unescape(text: str) -> str:
    """Turn literal ``\\r``/``\\n``/``\\t`` two-character sequences into real control chars.

    Args:
        text: Raw token text as returned by ``shlex.split``.

    Returns:
        *text* with ``\\r``, ``\\n``, and ``\\t`` replaced by the actual
        control characters they represent.
    """
    return text.replace("\\r", "\r").replace("\\n", "\n").replace("\\t", "\t")


def _parse_line(tokens: list[str], lineno: int) -> list[Keystroke]:
    """Parse one ``[WAIT ...] SEND ... DELAY ... [REPEAT ...]`` line into Keystrokes.

    Args:
        tokens: The line, already ``shlex.split`` into words.
        lineno: 1-based line number, used only for the error message.

    Returns:
        One ``Keystroke`` per repetition (``REPEAT count``, default 1); only
        the first carries *expect*.

    Raises:
        ValueError: *tokens* doesn't match the expected grammar.
    """
    try:
        pos = 0
        expect = None
        if tokens[pos] == "WAIT":
            expect, pos = tokens[pos + 1], pos + 2
        if tokens[pos] != "SEND":
            raise ValueError("expected SEND")
        keys_token, pos = tokens[pos + 1], pos + 2
        if tokens[pos] != "DELAY":
            raise ValueError("expected DELAY")
        delay, pos = float(tokens[pos + 1]), pos + 2
        repeat = 1
        if pos < len(tokens):
            if tokens[pos] != "REPEAT":
                raise ValueError("expected REPEAT")
            repeat = int(tokens[pos + 1])
    except (IndexError, ValueError) as exc:
        raise ValueError(f"line {lineno}: malformed keystroke: {tokens!r}") from exc

    keys = _KEY_ALIASES.get(keys_token, _unescape(keys_token))
    return [Keystroke(expect if i == 0 else None, keys, delay) for i in range(repeat)]


def _parse_keystrokes(text: str) -> list[Keystroke]:
    """Parse a keystroke script (see module docstring) into a list of Keystrokes.

    Args:
        text: The full keystroke script, as read from stdin.

    Returns:
        The scripted keystrokes, in order.
    """
    keystrokes: list[Keystroke] = []
    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        keystrokes.extend(_parse_line(shlex.split(line), lineno))
    return keystrokes


def _terminal_size() -> tuple[int, int]:
    """Return ``(rows, cols)`` of the enclosing terminal, falling back to a default.

    Returns:
        A ``(rows, cols)`` tuple: the real terminal size when stdout is a
        tty, otherwise ``(28, 116)``.
    """
    try:
        size = os.get_terminal_size(sys.stdout.fileno())
        return size.lines, size.columns
    except OSError:
        return 28, 116


def _pump(child: pexpect.spawn, duration: float) -> None:
    """Drain and mirror *child* output for *duration* seconds.

    Reading (rather than plain ``time.sleep``) is what keeps the mirrored
    output flowing to our own stdout in real time during a scripted pause,
    so the recorded pacing matches when a human would actually see it.

    Args:
        child: The pexpect-spawned dfetch process to read from.
        duration: How long to pause, in seconds.
    """
    deadline = time.monotonic() + duration
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return
        try:
            child.read_nonblocking(size=4096, timeout=min(_PUMP_SLICE, remaining))
        except pexpect.exceptions.TIMEOUT:
            continue
        except pexpect.exceptions.EOF:
            return


def _drive(child: pexpect.spawn, keystrokes: list[Keystroke]) -> None:
    """Feed *child* each scripted keystroke in order.

    Args:
        child: The pexpect-spawned dfetch process to drive.
        keystrokes: The scripted keystrokes, in order.
    """
    for step in keystrokes:
        if step.expect is not None:
            child.expect(step.expect)
        _pump(child, step.delay)
        child.send(step.keys)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(
            "Usage: <keystroke script on stdin> | interactive_helper.py <dfetch-args...>"
        )

    dfetch_args = sys.argv[1:]
    script_keystrokes = _parse_keystrokes(sys.stdin.read())
    if not script_keystrokes:
        sys.exit("No keystrokes provided on stdin")

    rows, cols = _terminal_size()

    dfetch_child = pexpect.spawn(
        "dfetch",
        dfetch_args,
        dimensions=(rows, cols),
        encoding="utf-8",
        timeout=120,
    )
    dfetch_child.logfile_read = sys.stdout

    _drive(dfetch_child, script_keystrokes)
    dfetch_child.expect(pexpect.EOF)
    dfetch_child.close()
    sys.exit(dfetch_child.exitstatus or 0)
