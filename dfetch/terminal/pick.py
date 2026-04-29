"""Scrollable single/multi-select pick list widget."""

from dfetch.terminal.ansi import BOLD, DIM, GREEN, RESET, VIEWPORT
from dfetch.terminal.keys import read_key
from dfetch.terminal.screen import Screen


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


def _initial_selection(
    multi: bool, all_selected: bool, n: int, default_idx: int
) -> set[int]:
    """Return the initial selected-indices set for a pick list."""
    if multi and all_selected:
        return set(range(n))
    if multi:
        return set()
    return {default_idx}


def _clamp_scroll(idx: int, top: int) -> int:
    """Return an updated *top* offset so that *idx* is visible in the viewport."""
    if idx < top:
        return idx
    if idx >= top + VIEWPORT:
        return idx - VIEWPORT + 1
    return top


def _render_pick_item(
    i: int, idx: int, item: str, selected: set[int], multi: bool
) -> str:
    """Format a single row for the pick widget."""
    cursor = f"{GREEN}▶{RESET}" if i == idx else " "
    check = f"{GREEN}✓ {RESET}" if (multi and i in selected) else "  "
    is_highlighted = (i in selected) if multi else (i == idx)
    styled = f"{BOLD}{item}{RESET}" if is_highlighted else item
    return f"  {cursor} {check}{styled}"


def _render_pick_lines(
    title: str,
    items: list[str],
    idx: int,
    top: int,
    selected: set[int],
    multi: bool,
) -> list[str]:
    """Build the list of lines to draw for one frame of the pick widget."""
    n = len(items)
    lines: list[str] = [f"  {BOLD}{title}{RESET}"]
    if top > 0:
        lines.append(f"    {DIM}↑ {top} more above{RESET}")
    for i in range(top, min(top + VIEWPORT, n)):
        lines.append(_render_pick_item(i, idx, items[i], selected, multi))
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
    if n == 0:
        screen.clear()
        return [] if multi else None
    selected = _initial_selection(multi, all_selected, n, default_idx)

    while True:
        idx = max(0, min(idx, n - 1))
        top = _clamp_scroll(idx, top)
        screen.draw(_render_pick_lines(title, display_items, idx, top, selected, multi))
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
