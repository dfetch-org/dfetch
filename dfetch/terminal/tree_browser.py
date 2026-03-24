"""Generic scrollable tree browser for remote VCS trees.

Provides :func:`run_tree_browser` and :func:`tree_single_pick` — interactive
terminal widgets that work with any :data:`~dfetch.terminal.LsFunction`.
"""

from __future__ import annotations

from dataclasses import dataclass

from dfetch.terminal.ansi import BOLD, DIM, GREEN, RESET, VIEWPORT, strip_ansi
from dfetch.terminal.keys import read_key
from dfetch.terminal.screen import Screen
from dfetch.terminal.types import LsFunction


@dataclass
class TreeNode:
    """One entry in the flattened view of a remote VCS tree."""

    name: str
    path: str  # path relative to repo root / tree prefix
    is_dir: bool
    depth: int = 0
    expanded: bool = False
    selected: bool = False
    children_loaded: bool = False


def _expand_node(nodes: list[TreeNode], idx: int, ls_function: LsFunction) -> None:
    """Expand the directory node at *idx*, loading children if not yet done."""
    node = nodes[idx]
    if not node.children_loaded:
        children = [
            TreeNode(
                name=name,
                path=f"{node.path}/{strip_ansi(name)}",
                is_dir=is_dir,
                depth=node.depth + 1,
                selected=node.selected,
            )
            for name, is_dir in ls_function(node.path)
        ]
        nodes[idx + 1 : idx + 1] = children
        node.children_loaded = True
    node.expanded = True


def _collapse_node(nodes: list[TreeNode], idx: int) -> None:
    """Collapse the directory node at *idx* and remove all descendant nodes."""
    parent_depth = nodes[idx].depth
    end = idx + 1
    while end < len(nodes) and nodes[end].depth > parent_depth:
        end += 1
    del nodes[idx + 1 : end]
    nodes[idx].expanded = False
    nodes[idx].children_loaded = False


def _render_tree_lines(
    nodes: list[TreeNode], idx: int, top: int, *, multi_select: bool = False
) -> list[str]:
    """Build the list of display strings for one frame of the tree browser."""
    n = len(nodes)
    lines: list[str] = []
    for i in range(top, min(top + VIEWPORT, n)):
        node = nodes[i]
        indent = "  " * node.depth
        icon = ("▾ " if node.expanded else "▸ ") if node.is_dir else "  "
        cursor = f"{GREEN}▶{RESET}" if i == idx else " "
        if multi_select:
            name = f"{DIM}{node.name}{RESET}" if not node.selected else node.name
            lines.append(f"  {cursor} {indent}{icon}{name}")
        else:
            check = f"{GREEN}✓ {RESET}" if node.selected else "  "
            name = f"{BOLD}{node.name}{RESET}" if i == idx else node.name
            lines.append(f"  {cursor} {check}{indent}{icon}{name}")
    return lines


def _cascade_selection(nodes: list[TreeNode], parent_idx: int, selected: bool) -> None:
    """Set *selected* on all loaded descendants of the node at *parent_idx*."""
    parent_depth = nodes[parent_idx].depth
    for i in range(parent_idx + 1, len(nodes)):
        if nodes[i].depth <= parent_depth:
            break
        nodes[i].selected = selected


def _adjust_scroll(idx: int, top: int) -> int:
    """Return a new *top* so that *idx* is within the visible viewport."""
    if idx < top:
        return idx
    if idx >= top + VIEWPORT:
        return idx - VIEWPORT + 1
    return top


def _build_tree_frame(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    title: str,
    nodes: list[TreeNode],
    idx: int,
    top: int,
    hint: str,
    *,
    multi_select: bool = False,
) -> list[str]:
    """Build all display lines for one render frame of the tree browser."""
    n = len(nodes)
    header = [f"  {BOLD}{title}{RESET}"]
    if top > 0:
        header.append(f"    {DIM}↑ {top} more above{RESET}")
    body = _render_tree_lines(nodes, idx, top, multi_select=multi_select)
    footer: list[str] = []
    remaining = n - (top + VIEWPORT)
    if remaining > 0:
        footer.append(f"    {DIM}↓ {remaining} more below{RESET}")
    footer.append(f"  {DIM}{hint}{RESET}")
    return header + body + footer


def _handle_tree_nav(key: str, idx: int, n: int) -> int | None:
    """Handle arrow/page navigation keys; return new index or None if not a nav key."""
    if key == "UP":
        return max(0, idx - 1)
    if key == "DOWN":
        return min(n - 1, idx + 1)
    if key == "PGUP":
        return max(0, idx - VIEWPORT)
    if key == "PGDN":
        return min(n - 1, idx + VIEWPORT)
    return None


def _handle_tree_left(nodes: list[TreeNode], idx: int) -> int:
    """Handle the LEFT key: collapse the current dir or jump to its parent."""
    node = nodes[idx]
    if node.is_dir and node.expanded:
        _collapse_node(nodes, idx)
        return idx
    if node.depth > 0:
        for i in range(idx - 1, -1, -1):
            if nodes[i].depth < node.depth:
                return i
    return idx


def _handle_tree_space(
    nodes: list[TreeNode], idx: int, multi: bool
) -> list[str] | None:
    """Handle SPACE: toggle selection (multi) or select immediately (single).

    Returns a path list when the browser should exit, or ``None`` to continue.
    """
    node = nodes[idx]
    if multi:
        node.selected = not node.selected
        if node.is_dir:
            _cascade_selection(nodes, idx, node.selected)
        return None
    return [node.path]


def _handle_tree_enter(
    nodes: list[TreeNode], idx: int, ls_function: LsFunction, multi: bool
) -> tuple[int, list[str] | None]:
    """Handle ENTER: confirm selection (multi), expand/collapse dir, or pick file."""
    node = nodes[idx]
    if multi:
        return idx, [n.path for n in nodes if n.selected]
    if node.is_dir:
        if node.expanded:
            _collapse_node(nodes, idx)
        else:
            _expand_node(nodes, idx, ls_function)
        return idx, None
    return idx, [node.path]


def _handle_tree_action(
    key: str,
    nodes: list[TreeNode],
    idx: int,
    ls_function: LsFunction,
    multi: bool,
) -> tuple[int, list[str] | None]:
    """Dispatch non-navigation keypresses.

    Returns ``(new_idx, result)``.  When *result* is not ``None`` the browser
    should exit and return it (``[]`` for ESC/skip, path list for a selection).
    """
    node = nodes[idx]
    if key == "RIGHT":
        if node.is_dir and not node.expanded:
            _expand_node(nodes, idx, ls_function)
        return idx, None
    if key == "LEFT":
        return _handle_tree_left(nodes, idx), None
    if key == "SPACE":
        return idx, _handle_tree_space(nodes, idx, multi)
    if key == "ENTER":
        return _handle_tree_enter(nodes, idx, ls_function, multi)
    if key == "ESC":
        return idx, []
    return idx, None


def run_tree_browser(
    ls_function: LsFunction,
    title: str,
    *,
    multi: bool,
    all_selected: bool = False,
) -> tuple[list[str], list[TreeNode]]:  # pragma: no cover - interactive TTY only
    """Core tree browser loop.

    Returns ``(selected_paths, final_nodes)``.  In single-select mode
    ``selected_paths`` has at most one item; in multi-select mode any number.
    ``final_nodes`` reflects the full node state at the time the user exits.
    """
    root_entries = ls_function("")
    if not root_entries:
        return [], []

    nodes: list[TreeNode] = [
        TreeNode(
            name=name,
            path=strip_ansi(name),
            is_dir=is_dir,
            depth=0,
            selected=all_selected,
        )
        for name, is_dir in root_entries
    ]
    hint = (
        "↑/↓ navigate  Space select  Enter confirm  →/← expand/collapse  Esc skip"
        if multi
        else "↑/↓ navigate  Enter/Space select  →/← expand/collapse  Esc skip"
    )
    screen = Screen()
    idx, top = 0, 0

    while True:
        n = len(nodes)
        if n == 0:
            screen.clear()
            return [], []
        idx = max(0, min(idx, n - 1))
        top = _adjust_scroll(idx, top)
        screen.draw(
            _build_tree_frame(title, nodes, idx, top, hint, multi_select=all_selected)
        )
        key = read_key()

        new_idx = _handle_tree_nav(key, idx, n)
        if new_idx is not None:
            idx = new_idx
            continue

        idx, result = _handle_tree_action(key, nodes, idx, ls_function, multi)
        if result is not None:
            screen.clear()
            return result, nodes


def tree_single_pick(ls_function: LsFunction, title: str) -> str:
    """Browse a remote tree and return a single selected path (``""`` on skip)."""
    result, _ = run_tree_browser(ls_function, title, multi=False)
    return result[0] if result else ""


def all_descendants_deselected(nodes: list[TreeNode], parent_idx: int) -> bool:
    """Return True if every loaded descendant of *parent_idx* is deselected."""
    parent_depth = nodes[parent_idx].depth
    for i in range(parent_idx + 1, len(nodes)):
        if nodes[i].depth <= parent_depth:
            break
        if nodes[i].selected:
            return False
    return True


def deselected_paths(nodes: list[TreeNode]) -> list[str]:
    """Compute minimal path list covering all deselected nodes.

    A deselected directory is emitted as a single entry when all its loaded
    descendants are also deselected (or it was never expanded).  This keeps
    the list short. Individual deselected files are listed when their
    parent directory is only partially deselected.
    """
    paths: list[str] = []
    dirs: set[str] = set()

    for i, node in enumerate(nodes):
        if node.selected:
            continue
        if any(node.path.startswith(d + "/") for d in dirs):
            continue
        if node.is_dir and (
            not node.children_loaded or all_descendants_deselected(nodes, i)
        ):
            paths.append(node.path)
            dirs.add(node.path)
        elif not node.is_dir:
            paths.append(node.path)

    return paths
