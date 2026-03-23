"""Low-level interactive terminal utilities.

Provides cross-platform raw-key reading, ANSI helpers, and a generic
scrollable single-pick list widget.  All symbols here are pure I/O
primitives with no dfetch domain knowledge.
"""

import os
import re
import sys
from collections.abc import Sequence

# ---------------------------------------------------------------------------
# ANSI escape sequences
# ---------------------------------------------------------------------------

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
    import msvcrt  # type: ignore[import]  # pylint: disable=import-outside-toplevel,import-error

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
        return arrow.get(msvcrt.getwch(), "UNKNOWN")  # type: ignore[attr-defined,no-any-return]
    if ch in ("\r", "\n"):
        return "ENTER"
    if ch == "\x1b":
        return "ESC"
    if ch == " ":
        return "SPACE"
    if ch == "\x03":
        raise KeyboardInterrupt
    return str(ch)  # ch is Any from untyped msvcrt


def _read_key_unix() -> str:  # pragma: no cover
    import select as _select  # pylint: disable=import-outside-toplevel
    import termios  # pylint: disable=import-outside-toplevel
    import tty  # pylint: disable=import-outside-toplevel

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


# ---------------------------------------------------------------------------
# Ghost prompt
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Scrollable pick widget
# ---------------------------------------------------------------------------


def _advance_pick_idx(key: str, idx: int, n: int) -> int:
    """Return the new cursor position after a navigation keypress."""
    if key == "UP":
        return max(0, idx - 1)
    if key == "DOWN":
        return min(n - 1, idx + 1)
    if key == "PGUP":
        return max(0, idx - VIEWPORT)
    return min(n - 1, idx + VIEWPORT)  # PGDN


def _toggle_pick_selection(idx: int, selected: set[int]) -> set[int]:
    """Return a new selected set with *idx* toggled."""
    new_sel = set(selected)
    if idx in new_sel:
        new_sel.discard(idx)
    else:
        new_sel.add(idx)
    return new_sel


def _pick_outcome(
    key: str, idx: int, selected: set[int], multi: bool
) -> tuple[bool, int | list[int] | None]:
    """Determine whether a keypress ends the interaction and what value to return.

    Returns ``(done, result)``.  When *done* is ``False`` the loop continues.
    When *done* is ``True``, *result* is the value to return to the caller.
    """
    if key == "ENTER":
        return True, sorted(selected) if multi else idx
    if key == "ESC":
        return True, None
    if key not in ("UP", "DOWN", "PGUP", "PGDN", "SPACE") and not multi:
        return True, None
    return False, None


def _clamp_scroll(idx: int, top: int) -> int:
    """Return an updated *top* offset so that *idx* is visible in the viewport."""
    if idx < top:
        return idx
    if idx >= top + VIEWPORT:
        return idx - VIEWPORT + 1
    return top


def _render_pick_lines(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    title: str,
    items: list[str],
    idx: int,
    top: int,
    selected: set[int],
    multi: bool,
    n: int,
) -> list[str]:
    """Build the list of lines to draw for one frame of the pick widget."""
    lines: list[str] = [f"  {BOLD}{title}{RESET}"]
    if top > 0:
        lines.append(f"    {DIM}↑ {top} more above{RESET}")
    for i in range(top, min(top + VIEWPORT, n)):
        cursor = f"{YELLOW}▶{RESET}" if i == idx else " "
        check = f"{GREEN}✓ {RESET}" if (multi and i in selected) else "  "
        item_text = items[i]
        is_highlighted = (i in selected) if multi else (i == idx)
        styled = f"{BOLD}{item_text}{RESET}" if is_highlighted else item_text
        lines.append(f"  {cursor} {check}{styled}")
    remaining = n - (top + VIEWPORT)
    if remaining > 0:
        lines.append(f"    {DIM}↓ {remaining} more below{RESET}")
    hint = (
        "↑/↓ navigate  Space toggle  Enter confirm  Esc skip"
        if multi
        else "↑/↓ navigate  PgUp/PgDn jump  Enter select  Esc free-type"
    )
    lines.append(f"  {DIM}{hint}{RESET}")
    return lines


def scrollable_pick(
    title: str,
    display_items: list[str],
    *,
    default_idx: int = 0,
    multi: bool = False,
    all_selected: bool = False,
) -> int | list[int] | None:  # pragma: no cover – interactive TTY only
    """Display a scrollable pick list; return selected index or indices.

    *display_items* are plain strings (no ANSI codes).  Navigate with
    ↑/↓ or PgUp/PgDn.  In single-select mode (``multi=False``) confirm
    with Enter; in multi-select mode (``multi=True``) toggle with Space
    and confirm with Enter.  Cancel with Esc (returns ``None``).

    Single-select: returns the selected index.
    Multi-select: returns a list of selected indices (may be empty).
    If ``all_selected=True``, starts with all items selected.
    """
    screen = Screen()
    idx = default_idx
    top = 0
    n = len(display_items)
    selected: set[int] = (
        set(range(n))
        if (multi and all_selected)
        else ({default_idx} if not multi else set())
    )

    while True:
        idx = max(0, min(idx, n - 1))
        top = _clamp_scroll(idx, top)
        screen.draw(
            _render_pick_lines(title, display_items, idx, top, selected, multi, n)
        )
        key = read_key()

        if key in ("UP", "DOWN", "PGUP", "PGDN"):
            idx = _advance_pick_idx(key, idx, n)
        elif key == "SPACE" and multi:
            selected = _toggle_pick_selection(idx, selected)
        else:
            done, result = _pick_outcome(key, idx, selected, multi)
            if done:
                screen.clear()
                return result
