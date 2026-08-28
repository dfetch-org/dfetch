#!/usr/bin/env python3
"""Drive an interactive dfetch command through a real pty for asciinema recordings.

Usage::

    python3 interactive_helper.py <dfetch-args...>

Interactive dfetch commands (like ``add -i``) use a real interactive-terminal
UI -- ghost-text prompts, hierarchical tree browsers -- that reads raw
keypresses straight from the terminal, so there is nothing to mock at the
Python level; the only way to automate a recording of one is to actually
drive a terminal.

This script spawns ``dfetch`` inside its own pty (via ``pexpect``) and feeds
it a scripted list of keystrokes (see ``INTERACTIVE_ADD_KEYSTROKES`` below),
each preceded by a pattern to wait for and a delay that simulates human
timing. Everything the inner pty prints is mirrored to this script's own
stdout as it arrives, so when this script is itself run under
``asciinema rec -c``, the recorder captures dfetch's real terminal output
with real timing -- and no human needs to be at the keyboard.

To script a recording for another interactive command, add a new keystroke
list next to ``INTERACTIVE_ADD_KEYSTROKES`` and register it in
``_KEYSTROKES_BY_SUBCOMMAND``.
"""

from __future__ import annotations

import dataclasses
import os
import sys
import time

import pexpect

# ---------------------------------------------------------------------------
# Timing (seconds), tuned to match doc/asciicasts/interactive-add.cast's pacing
# ---------------------------------------------------------------------------
_PRE_DELAY = 1.3  # pause before accepting/typing a field, to simulate "thinking"
_STEP_DELAY = 0.35  # pause between arrow-key presses while browsing a tree
_CONFIRM_DELAY = 0.9  # pause before the Enter that accepts a tree pick
_READ_DELAY = 1.8  # longer pause where a human lingers to read a list
_PUMP_SLICE = 0.02  # granularity for draining/mirroring output while paused

DOWN = "\x1b[B"
ENTER = "\r"
SPACE = " "


@dataclasses.dataclass(frozen=True)
class Keystroke:
    """One scripted input to send to the driven dfetch process.

    *expect* is a regex to wait for before sending *keys*; ``None`` sends
    right after the previous keystroke's delay, for runs of repeated presses
    (e.g. stepping down a tree). *delay* is how long to pause -- draining and
    mirroring output the whole time -- before sending *keys*.
    """

    expect: str | None
    keys: str
    delay: float


def _downs(
    count: int, *, delay: float = _STEP_DELAY, first_expect: str | None = None
) -> list[Keystroke]:
    """*count* Down-arrow presses in a row; only the first waits on *first_expect*."""
    return [
        Keystroke(first_expect if i == 0 else None, DOWN, delay) for i in range(count)
    ]


# The choices shown in doc/asciicasts/interactive-add.cast: accept the
# default name/destination, pick the v3.4 tag, keep the whole repository as
# src, and ignore examples/ and tests/.
INTERACTIVE_ADD_KEYSTROKES: list[Keystroke] = [
    Keystroke("Name:", ENTER, _PRE_DELAY),  # accept default name (cpputest)
    Keystroke("Destination:", ENTER, _PRE_DELAY),  # accept default destination
    *_downs(7, first_expect="Enter select"),  # master -> 3.7.2 -> ... -> v3.4
    Keystroke(None, ENTER, _CONFIRM_DELAY),
    Keystroke("Esc skip", ENTER, _READ_DELAY),  # accept "." (fetch whole repo)
    *_downs(5, first_expect="Space toggle"),  # . -> .settings -> ... -> examples
    Keystroke(None, SPACE, _STEP_DELAY),  # deselect examples/
    *_downs(7),  # examples -> include -> ... -> src -> tests
    Keystroke(None, SPACE, _STEP_DELAY),  # deselect tests/
    Keystroke(None, ENTER, _CONFIRM_DELAY),
    Keystroke("Add project to manifest?", f"y{ENTER}", _PRE_DELAY),
    Keystroke(r"Run '.*' now\?", f"n{ENTER}", _PRE_DELAY),
]

_KEYSTROKES_BY_SUBCOMMAND: dict[str, list[Keystroke]] = {
    "add": INTERACTIVE_ADD_KEYSTROKES,
}


def _terminal_size() -> tuple[int, int]:
    """Return ``(rows, cols)`` of the enclosing terminal, falling back to a default."""
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
    """Feed *child* each scripted keystroke in order."""
    for step in keystrokes:
        if step.expect is not None:
            child.expect(step.expect)
        _pump(child, step.delay)
        child.send(step.keys)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: interactive_helper.py <dfetch-args...>")

    dfetch_args = sys.argv[1:]
    subcommand = dfetch_args[0]
    keystrokes = _KEYSTROKES_BY_SUBCOMMAND.get(subcommand)
    if keystrokes is None:
        sys.exit(f"No scripted keystrokes for 'dfetch {subcommand}'")

    rows, cols = _terminal_size()

    dfetch_child = pexpect.spawn(
        "dfetch",
        dfetch_args,
        dimensions=(rows, cols),
        encoding="utf-8",
        timeout=120,
    )
    dfetch_child.logfile_read = sys.stdout

    _drive(dfetch_child, keystrokes)
    dfetch_child.expect(pexpect.EOF)
    dfetch_child.close()
    sys.exit(dfetch_child.exitstatus or 0)
