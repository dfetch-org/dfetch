"""Single-line ghost prompt."""

import sys

from .ansi import DIM, RESET
from .keys import read_key


def _ghost_handle_backspace(buf: list[str], ghost_active: bool, ghost_len: int) -> bool:
    """Handle backspace in a ghost prompt; returns updated *ghost_active*."""
    if buf:
        buf.pop()
        sys.stdout.write("\x1b[1D\x1b[K")
        sys.stdout.flush()
    elif ghost_active:
        sys.stdout.write(f"\x1b[{ghost_len}D\x1b[K")
        sys.stdout.flush()
        return False
    return ghost_active


def _ghost_handle_char(
    ch: str, buf: list[str], ghost_active: bool, ghost_len: int
) -> bool:
    """Append *ch* to *buf*, clearing ghost if still active; returns updated *ghost_active*."""
    if ghost_active:
        sys.stdout.write(f"\x1b[{ghost_len}D\x1b[K{ch}")
        ghost_active = False
    else:
        sys.stdout.write(ch)
    sys.stdout.flush()
    buf.append(ch)
    return ghost_active


def ghost_prompt(label: str, default: str = "") -> str:  # pragma: no cover
    """Single-line prompt with *default* shown as dim ghost text.

    The ghost disappears the moment the user types anything.
    Pressing Enter with no input accepts *default*.
    """
    sys.stdout.write(f"{label}: {DIM}{default}{RESET}")
    sys.stdout.flush()

    buf: list[str] = []
    ghost_active = bool(default)

    while True:
        key = read_key()
        if key == "ENTER":
            sys.stdout.write("\n")
            sys.stdout.flush()
            return "".join(buf) if buf else default
        if key in ("\x7f", "\x08"):
            ghost_active = _ghost_handle_backspace(buf, ghost_active, len(default))
            continue
        ch = " " if key == "SPACE" else key
        if len(ch) == 1 and ch.isprintable():
            ghost_active = _ghost_handle_char(ch, buf, ghost_active, len(default))
