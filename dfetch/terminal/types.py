"""Type aliases for the terminal package."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class Entry:
    """One entry returned by an :data:`LsFunction`.

    *display* is the string shown in the tree browser.  *value* is the
    underlying path segment used when building ``node.path``; it defaults
    to *display* when not supplied, which is correct for plain file trees
    where the two are identical.  Set *value* explicitly when the display
    carries decorations (ANSI codes, kind labels, etc.) that should not
    bleed into the path.

    *has_children* indicates whether the entry can be expanded further.
    For file trees this corresponds to directories; for other uses (e.g.
    a version picker) it marks namespace groups that contain nested items.
    """

    display: str
    has_children: bool
    value: str = field(default="")

    def __post_init__(self) -> None:
        """Default *value* to *display* when not explicitly provided."""
        if not self.value:
            self.value = self.display


LsFunction = Callable[[str], list[Entry]]
