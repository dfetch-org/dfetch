"""Low-level interactive terminal utilities.

Provides cross-platform raw-key reading, ANSI helpers, and a generic
scrollable single-pick list widget.  All symbols here are pure I/O
primitives with no dfetch domain knowledge.
"""

import os
import sys
from collections.abc import Sequence

# ---------------------------------------------------------------------------
# ANSI escape sequences
# ---------------------------------------------------------------------------

RESET = "\x1b[0m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"
REVERSE = "\x1b[7m"  # swap fore/background – used for cursor highlight
CYAN = "\x1b[36m"
MAGENTA = "\x1b[35m"
GREEN = "\x1b[32m"
YELLOW = "\x1b[33m"

# Viewport height for scrollable list widgets (number of items shown at once).
VIEWPORT = 10


# ---------------------------------------------------------------------------
# TTY detection
# ---------------------------------------------------------------------------


def is_tty() -> bool:
    """Return True when stdin is an interactive terminal (not CI, not piped)."""
    return sys.stdin.isatty() and not os.environ.get("CI")


# ---------------------------------------------------------------------------
# Raw key reading
# ---------------------------------------------------------------------------


def read_key() -> str:  # pragma: no cover – requires live terminal
    """Read one keypress from stdin in raw mode; return a normalised key name.

    Possible return values: ``"UP"``, ``"DOWN"``, ``"LEFT"``, ``"RIGHT"``,
    ``"PGUP"``, ``"PGDN"``, ``"ENTER"``, ``"SPACE"``, ``"ESC"``, or a
    single printable character string.

    Raises ``KeyboardInterrupt`` on Ctrl-C / Ctrl-D.
    """
    if sys.platform == "win32":
        return _read_key_windows()
    return _read_key_unix()


def _read_key_windows() -> str:  # pragma: no cover
    import msvcrt  # type: ignore[import]

    ch = msvcrt.getwch()  # type: ignore[attr-defined]
    if ch in ("\x00", "\xe0"):
        arrow = {
            "H": "UP",
            "P": "DOWN",
            "K": "LEFT",
            "M": "RIGHT",
            "I": "PGUP",
            "Q": "PGDN",
        }
        return arrow.get(msvcrt.getwch(), "UNKNOWN")  # type: ignore[attr-defined]
    if ch in ("\r", "\n"):
        return "ENTER"
    if ch == "\x1b":
        return "ESC"
    if ch == " ":
        return "SPACE"
    if ch == "\x03":
        raise KeyboardInterrupt
    return ch


def _read_key_unix() -> str:  # pragma: no cover
    import select as _select
    import termios
    import tty

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = os.read(fd, 1)

        if ch in (b"\r", b"\n"):
            return "ENTER"

        if ch == b"\x1b":
            readable, _, _ = _select.select([fd], [], [], 0.05)
            if readable:
                rest = b""
                while True:
                    more, _, _ = _select.select([fd], [], [], 0.01)
                    if not more:
                        break
                    rest += os.read(fd, 1)
                escape_sequences = {
                    b"\x1b[A": "UP",
                    b"\x1b[B": "DOWN",
                    b"\x1b[C": "RIGHT",
                    b"\x1b[D": "LEFT",
                    b"\x1b[5~": "PGUP",
                    b"\x1b[6~": "PGDN",
                }
                return escape_sequences.get(ch + rest, "ESC")
            return "ESC"

        if ch == b" ":
            return "SPACE"
        if ch in (b"\x03", b"\x04"):
            raise KeyboardInterrupt

        return ch.decode("utf-8", errors="replace")
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


# ---------------------------------------------------------------------------
# In-place screen redraw
# ---------------------------------------------------------------------------


class Screen:
    """Minimal ANSI helper for in-place redraw.

    Tracks the number of lines last written so that each ``draw()`` call
    moves the cursor back up and overwrites them without flicker.
    """

    def __init__(self) -> None:
        self._line_count = 0

    def draw(self, lines: Sequence[str]) -> None:
        """Overwrite the previously drawn content with *lines*."""
        if self._line_count:
            sys.stdout.write(f"\x1b[{self._line_count}A\x1b[0J")
        sys.stdout.write("\n".join(lines) + "\n")
        sys.stdout.flush()
        self._line_count = len(lines)

    def clear(self) -> None:
        """Erase the previously drawn content."""
        if self._line_count:
            sys.stdout.write(f"\x1b[{self._line_count}A\x1b[0J")
            sys.stdout.flush()
            self._line_count = 0


# ---------------------------------------------------------------------------
# Scrollable pick widget
# ---------------------------------------------------------------------------


def scrollable_pick(
    title: str,
    display_items: list[str],
    *,
    default_idx: int = 0,
) -> int | None:  # pragma: no cover – interactive TTY only
    """Display a scrollable single-pick list; return the selected index or None on Esc.

    *display_items* are pre-formatted display strings (may contain raw ANSI
    codes).  Navigate with ↑/↓ or PgUp/PgDn; confirm with Enter; cancel
    with Esc (returns ``None``).
    """
    screen = Screen()
    idx = default_idx
    top = 0
    n = len(display_items)

    while True:
        idx = max(0, min(idx, n - 1))
        if idx < top:
            top = idx
        elif idx >= top + VIEWPORT:
            top = idx - VIEWPORT + 1

        lines: list[str] = [f"  {BOLD}{title}{RESET}"]
        for i in range(top, min(top + VIEWPORT, n)):
            cursor = f"{YELLOW}▶{RESET}" if i == idx else " "
            highlight_start = REVERSE if i == idx else ""
            highlight_end = RESET if i == idx else ""
            lines.append(
                f"  {cursor} {highlight_start}{display_items[i]}{highlight_end}"
            )

        if top > 0:
            lines.append(f"    {DIM}↑ {top} more above{RESET}")
        remaining = n - (top + VIEWPORT)
        if remaining > 0:
            lines.append(f"    {DIM}↓ {remaining} more below{RESET}")
        lines.append(
            f"  {DIM}↑/↓ navigate  PgUp/PgDn jump  Enter select  Esc free-type{RESET}"
        )

        screen.draw(lines)
        key = read_key()

        if key == "UP":
            idx -= 1
        elif key == "DOWN":
            idx += 1
        elif key == "PGUP":
            idx = max(0, idx - VIEWPORT)
        elif key == "PGDN":
            idx = min(n - 1, idx + VIEWPORT)
        elif key == "ENTER":
            screen.clear()
            return idx
        elif key == "ESC":
            screen.clear()
            return None
