"""Interactive terminal utilities.

All public symbols are re-exported here for convenient access via
``from dfetch.terminal import X``.  Implementation lives in the
sub-modules: :mod:`ansi`, :mod:`keys`, :mod:`screen`, :mod:`prompt`,
:mod:`pick`, :mod:`tree_browser`.
"""

from .ansi import (
    BOLD,
    CYAN,
    DIM,
    GREEN,
    MAGENTA,
    RESET,
    REVERSE,
    VIEWPORT,
    YELLOW,
    strip_ansi,
)
from .keys import is_tty, read_key
from .pick import scrollable_pick
from .prompt import ghost_prompt, numbered_prompt, prompt
from .screen import Screen, erase_last_line
from .tree_browser import tree_pick_from_names
from .types import Entry, LsFunction

__all__ = [
    "BOLD",
    "CYAN",
    "DIM",
    "GREEN",
    "Entry",
    "LsFunction",
    "MAGENTA",
    "RESET",
    "REVERSE",
    "VIEWPORT",
    "YELLOW",
    "Screen",
    "erase_last_line",
    "ghost_prompt",
    "numbered_prompt",
    "prompt",
    "is_tty",
    "read_key",
    "scrollable_pick",
    "strip_ansi",
    "tree_pick_from_names",
]
