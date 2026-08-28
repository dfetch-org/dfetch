#!/usr/bin/env python3
"""Drive ``dfetch add -i`` through a real pty for asciinema recordings.

Usage::

    python3 interactive_add_helper.py <remote-url>

``dfetch add -i`` always uses its real interactive-terminal UI (ghost-text
prompts for name/destination, a hierarchical tree browser for
version/src/ignore) -- the UI documented in ``doc/howto/adding-a-project.rst``
and shown in ``doc/asciicasts/interactive-add.cast``. That UI reads raw
keypresses straight from the terminal, so there is nothing to mock at the
Python level; the only way to automate it is to actually drive a terminal.

This script does that by spawning ``dfetch`` inside its own pty (via
``pexpect``) and feeding it the same choices shown in the current cast, on a
timer: accept the default name/destination, use the version tree to pick the
``v3.4`` tag, accept the whole repository as ``src``, then use the ignore
tree to exclude ``examples/`` and ``tests/``.

Everything the inner pty prints is mirrored to this script's own stdout as
it arrives, so when this script is itself run under ``asciinema rec -c``,
the recorder captures dfetch's real terminal output with real timing --
and no human needs to be at the keyboard.
"""

from __future__ import annotations

import os
import sys
import time

import pexpect

_PRE_DELAY = 1.3  # pause before pressing a key, to simulate "thinking"
_STEP_DELAY = 0.35  # pause between arrow-key presses while browsing a tree
_CONFIRM_DELAY = 0.9  # pause before the Enter that accepts a tree pick
_READ_DELAY = 1.8  # longer pause where the original recording lingers to read
_PUMP_SLICE = 0.02  # granularity for draining/mirroring output while paused

DOWN = "\x1b[B"
ENTER = "\r"
SPACE = " "


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


def _press(child: pexpect.spawn, keys: str, *, delay: float = _STEP_DELAY) -> None:
    """Pause *delay* seconds (mirroring output), then send *keys*."""
    _pump(child, delay)
    child.send(keys)


def _navigate(child: pexpect.spawn, steps: int, *, delay: float = _STEP_DELAY) -> None:
    """Press Down *steps* times, pausing *delay* seconds between presses."""
    for _ in range(steps):
        _press(child, DOWN, delay=delay)


def _drive_wizard(child: pexpect.spawn) -> None:
    """Feed the wizard the same choices shown in ``doc/asciicasts/interactive-add.cast``."""
    child.expect("Name:")
    _press(child, ENTER, delay=_PRE_DELAY)  # accept default name (cpputest)

    child.expect("Destination:")
    _press(child, ENTER, delay=_PRE_DELAY)  # accept default destination

    child.expect("Enter select")  # version tree browser has been drawn
    _navigate(child, 7)  # master -> 3.7.2 -> gh-pages -> ... -> v3.4
    _press(child, ENTER, delay=_CONFIRM_DELAY)

    child.expect("Esc skip")  # source-path tree browser has been drawn
    _press(child, ENTER, delay=_READ_DELAY)  # accept "." (fetch whole repo)

    child.expect("Space toggle")  # ignore tree browser has been drawn
    _navigate(child, 5)  # . -> .settings -> build -> cmake -> docs -> examples
    _press(child, SPACE, delay=_STEP_DELAY)  # deselect examples/
    _navigate(child, 7)  # examples -> include -> ... -> src -> tests
    _press(child, SPACE, delay=_STEP_DELAY)  # deselect tests/
    _press(child, ENTER, delay=_CONFIRM_DELAY)

    child.expect("Add project to manifest?")
    _press(child, f"y{ENTER}", delay=_PRE_DELAY)

    child.expect(r"Run '.*' now\?")
    _press(child, f"n{ENTER}", delay=_PRE_DELAY)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: interactive_add_helper.py <remote-url>")

    url = sys.argv[1]
    rows, cols = _terminal_size()

    dfetch_child = pexpect.spawn(
        "dfetch",
        ["add", "--interactive", url],
        dimensions=(rows, cols),
        encoding="utf-8",
        timeout=120,
    )
    dfetch_child.logfile_read = sys.stdout

    _drive_wizard(dfetch_child)
    dfetch_child.expect(pexpect.EOF)
    dfetch_child.close()
    sys.exit(dfetch_child.exitstatus or 0)
