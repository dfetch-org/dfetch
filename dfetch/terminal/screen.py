"""In-place terminal screen redraw."""

import sys
from collections.abc import Sequence

from .keys import is_tty


def erase_last_line() -> None:
    """Erase the most recently printed terminal line (no-op when not a TTY)."""
    if is_tty():
        sys.stdout.write("\x1b[1A\x1b[2K")
        sys.stdout.flush()


class Screen:
    """Minimal ANSI helper for in-place redraw.

    Tracks the number of lines last written so that each ``draw()`` call
    moves the cursor back up and overwrites them without flicker.
    """

    def __init__(self) -> None:
        """Create screen."""
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
