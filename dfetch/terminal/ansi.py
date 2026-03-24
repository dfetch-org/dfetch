"""ANSI escape sequences and text-stripping utilities."""

import re

RESET = "\x1b[0m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"
REVERSE = "\x1b[7m"  # swap fore/background – used for cursor highlight
CYAN = "\x1b[96m"
MAGENTA = "\x1b[95m"
GREEN = "\x1b[92m"
YELLOW = "\x1b[93m"

# Viewport height for scrollable list widgets (number of items shown at once).
VIEWPORT = 10

_ANSI_ESC_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(s: str) -> str:
    """Strip ANSI colour/style escape sequences from *s*."""
    return _ANSI_ESC_RE.sub("", s)
