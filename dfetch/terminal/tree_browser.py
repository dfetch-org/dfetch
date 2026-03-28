"""Generic scrollable tree browser for remote VCS trees.

Provides :func:`run_tree_browser`, :func:`tree_single_pick`, and
:func:`tree_pick_from_names` — interactive terminal widgets that work with
any :data:`~dfetch.terminal.LsFunction`.
"""

from __future__ import annotations

from dataclasses import dataclass

from dfetch.terminal.ansi import BOLD, DIM, GREEN, RESET, VIEWPORT
from dfetch.terminal.keys import read_key
from dfetch.terminal.screen import Screen
from dfetch.terminal.types import Entry, LsFunction


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


@dataclass(frozen=True)
class BrowserConfig:
    """Configuration for a :class:`TreeBrowser` session."""

    multi: bool = False
    all_selected: bool = False
    dirs_selectable: bool = False
    esc_label: str = "skip"


class TreeBrowser:
    """Interactive scrollable tree browser for a remote VCS tree."""

    def __init__(
        self,
        ls_function: LsFunction,
        title: str,
        config: BrowserConfig = BrowserConfig(),
    ) -> None:
        """Initialise browser configuration; call :meth:`run` to start."""
        self._ls_function = ls_function
        self._title = title
        self._config = config
        self._nodes: list[TreeNode] = []
        self._idx = 0
        self._top = 0

    @property
    def nodes(self) -> list[TreeNode]:
        """Current node list (populated after :meth:`run`)."""
        return self._nodes

    # ------------------------------------------------------------------
    # Scroll
    # ------------------------------------------------------------------

    def _adjust_scroll(self) -> None:
        """Ensure the cursor index is within the visible viewport."""
        if self._idx < self._top:
            self._top = self._idx
        elif self._idx >= self._top + VIEWPORT:
            self._top = self._idx - VIEWPORT + 1

    def _scroll_to_reveal_first_child(self) -> None:
        """Scroll down one row when an expanded dir sits at the viewport bottom."""
        node = self._nodes[self._idx]
        if (
            node.is_dir
            and node.expanded
            and self._idx == self._top + VIEWPORT - 1
            and self._idx + 1 < len(self._nodes)
        ):
            self._top += 1

    # ------------------------------------------------------------------
    # Node mutation
    # ------------------------------------------------------------------

    def _expand(self, idx: int) -> None:
        """Expand the directory node at *idx*, loading children if needed."""
        node = self._nodes[idx]
        if not node.children_loaded:
            children = [
                TreeNode(
                    name=entry.display,
                    path=f"{node.path}/{entry.value}",
                    is_dir=entry.has_children,
                    depth=node.depth + 1,
                    selected=node.selected,
                )
                for entry in self._ls_function(node.path)
            ]
            self._nodes[idx + 1 : idx + 1] = children
            node.children_loaded = True
        node.expanded = True

    def _collapse(self, idx: int) -> None:
        """Collapse the directory node at *idx* and remove all descendants."""
        parent_depth = self._nodes[idx].depth
        end = idx + 1
        while end < len(self._nodes) and self._nodes[end].depth > parent_depth:
            end += 1
        del self._nodes[idx + 1 : end]
        self._nodes[idx].expanded = False
        self._nodes[idx].children_loaded = False

    def _cascade_selection(self, parent_idx: int, selected: bool) -> None:
        """Set *selected* on all loaded descendants of *parent_idx*."""
        parent_depth = self._nodes[parent_idx].depth
        for i in range(parent_idx + 1, len(self._nodes)):
            if self._nodes[i].depth <= parent_depth:
                break
            self._nodes[i].selected = selected

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _nav_hint(self) -> str:
        """Return the bottom navigation hint line."""
        esc = self._config.esc_label
        if self._config.multi:
            return (
                f"↑/↓ navigate  Space toggle  Enter confirm"
                f"  →/← expand/collapse  Esc {esc}"
            )
        return f"↑/↓ navigate  Enter select  →/← expand/collapse  Esc {esc}"

    def _render_node(self, i: int, node: TreeNode) -> str:
        """Render a single node row for the visible viewport."""
        indent = "  " * node.depth
        icon = ("▾ " if node.expanded else "▸ ") if node.is_dir else "  "
        cursor = f"{GREEN}▶{RESET}" if i == self._idx else " "
        if self._config.multi:
            name = f"{DIM}{node.name}{RESET}" if not node.selected else node.name
            return f"  {cursor} {indent}{icon}{name}"
        check = f"{GREEN}✓ {RESET}" if node.selected else "  "
        name = f"{BOLD}{node.name}{RESET}" if i == self._idx else node.name
        return f"  {cursor} {check}{indent}{icon}{name}"

    def _render_lines(self) -> list[str]:
        """Build display strings for the visible viewport slice."""
        return [
            self._render_node(i, self._nodes[i])
            for i in range(self._top, min(self._top + VIEWPORT, len(self._nodes)))
        ]

    def _build_frame(self) -> list[str]:
        """Build all display lines for one render frame."""
        header = [f"  {GREEN}?{RESET} {BOLD}{self._title}:{RESET}"]
        if self._top > 0:
            header.append(f"    {DIM}↑ {self._top} more above{RESET}")
        footer: list[str] = []
        hidden_below = len(self._nodes) - (self._top + VIEWPORT)
        if hidden_below > 0:
            footer.append(f"    {DIM}↓ {hidden_below} more below{RESET}")
        footer.append(f"  {DIM}{self._nav_hint()}{RESET}")
        return header + self._render_lines() + footer

    # ------------------------------------------------------------------
    # Key handlers
    # ------------------------------------------------------------------

    def _handle_nav(self, key: str) -> bool:
        """Handle arrow/page keys; mutate *_idx* and return True if handled."""
        n = len(self._nodes)
        if key == "UP":
            self._idx = max(0, self._idx - 1)
        elif key == "DOWN":
            self._idx = min(n - 1, self._idx + 1)
        elif key == "PGUP":
            self._idx = max(0, self._idx - VIEWPORT)
        elif key == "PGDN":
            self._idx = min(n - 1, self._idx + VIEWPORT)
        else:
            return False
        return True

    def _handle_left(self) -> None:
        """Collapse the current dir or jump to its parent."""
        node = self._nodes[self._idx]
        if node.is_dir and node.expanded:
            self._collapse(self._idx)
            return
        if node.depth > 0:
            for i in range(self._idx - 1, -1, -1):
                if self._nodes[i].depth < node.depth:
                    self._idx = i
                    return

    def _handle_space(self) -> list[str] | None:
        """Toggle selection (multi) or select immediately (single)."""
        node = self._nodes[self._idx]
        if self._config.multi:
            node.selected = not node.selected
            if node.is_dir:
                self._cascade_selection(self._idx, node.selected)
            return None
        return [node.path]

    def _handle_enter(self) -> list[str] | None:
        """Confirm selection (multi), pick node (dirs_selectable), expand/collapse, or pick leaf."""
        node = self._nodes[self._idx]
        if self._config.multi:
            return [item.path for item in self._nodes if item.selected]
        if node.is_dir:
            if self._config.dirs_selectable:
                return [node.path]
            if node.expanded:
                self._collapse(self._idx)
            else:
                self._expand(self._idx)
            return None
        return [node.path]

    def _handle_right(self, node: TreeNode) -> None:
        """Expand the current directory on RIGHT, if not already open."""
        if node.is_dir and not node.expanded:
            self._expand(self._idx)

    def _handle_action(self, key: str) -> list[str] | None:
        """Dispatch a non-navigation keypress; return a result list or None to continue."""
        node = self._nodes[self._idx]
        if key == "RIGHT":
            self._handle_right(node)
        elif key == "LEFT":
            self._handle_left()
        elif key == "SPACE":
            return (
                self._handle_enter() if not self._config.multi else self._handle_space()
            )
        elif key == "ENTER":
            return self._handle_enter()
        elif key == "ESC":
            return []
        return None

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> list[str]:  # pragma: no cover - interactive TTY only
        """Run the interactive browser; return selected paths (empty list on skip)."""
        root_entries = self._ls_function("")
        if not root_entries:
            return []

        self._nodes = [
            TreeNode(
                name=entry.display,
                path=entry.value,
                is_dir=entry.has_children,
                depth=0,
                selected=self._config.all_selected,
            )
            for entry in root_entries
        ]

        if len(self._nodes) == 1 and self._nodes[0].is_dir:
            self._expand(0)

        screen = Screen()

        while True:
            self._idx = max(0, min(self._idx, len(self._nodes) - 1))
            self._adjust_scroll()
            screen.draw(self._build_frame())
            key = read_key()

            if self._handle_nav(key):
                continue

            result = self._handle_action(key)
            if result is not None:
                screen.clear()
                return result
            self._scroll_to_reveal_first_child()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_tree_browser(
    ls_function: LsFunction,
    title: str,
    config: BrowserConfig,
) -> tuple[list[str], list[TreeNode]]:  # pragma: no cover - interactive TTY only
    """Run a tree browser and return ``(selected_paths, final_nodes)``.

    In single-select mode ``selected_paths`` has at most one item; in
    multi-select mode any number.  ``final_nodes`` reflects the full node
    state at the time the user exits.
    """
    browser = TreeBrowser(ls_function, title, config)
    return browser.run(), browser.nodes


def tree_single_pick(
    ls_function: LsFunction,
    title: str,
    *,
    dirs_selectable: bool = False,
    esc_label: str = "skip",
) -> str:  # pragma: no cover - interactive TTY only
    """Browse a remote tree and return a single selected path (``""`` on skip)."""
    config = BrowserConfig(dirs_selectable=dirs_selectable, esc_label=esc_label)
    browser = TreeBrowser(ls_function, title, config)
    result = browser.run()
    return result[0] if result else ""


# ---------------------------------------------------------------------------
# Tree analysis helpers
# ---------------------------------------------------------------------------


def all_descendants_deselected(nodes: list[TreeNode], parent_idx: int) -> bool:
    """Return True if every loaded descendant of *parent_idx* is deselected."""
    parent_depth = nodes[parent_idx].depth
    for i in range(parent_idx + 1, len(nodes)):
        if nodes[i].depth <= parent_depth:
            break
        if nodes[i].selected:
            return False
    return True


def _is_covered_by_dir(path: str, dirs: set[str]) -> bool:
    """Return True if *path* is nested under any directory in *dirs*."""
    return any(path.startswith(d + "/") for d in dirs)


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
        if _is_covered_by_dir(node.path, dirs):
            continue
        if node.is_dir and (
            not node.children_loaded or all_descendants_deselected(nodes, i)
        ):
            paths.append(node.path)
            dirs.add(node.path)
        elif not node.is_dir:
            paths.append(node.path)

    return paths


# ---------------------------------------------------------------------------
# Flat-name tree browser
# ---------------------------------------------------------------------------


class _FlatNamesLs:  # pylint: disable=too-few-public-methods
    """LsFunction that exposes a flat list of slash-separated names as a tree.

    Leaf nodes carry a dim annotation label so they are visually distinct from
    directory segments.  The tree browser uses ``Entry.value`` (the plain name)
    rather than ``Entry.display`` (which may contain markup).
    """

    def __init__(
        self, labels: dict[str, str], all_names: list[str], priority_path: str
    ) -> None:
        """Store pre-built lookup tables and the path to sort first."""
        self._labels = labels
        self._all_names = all_names
        self._priority_path = priority_path

    def _segments(self, prefix: str) -> dict[str, bool]:
        """Return first-level path segments under *prefix* mapped to has_children."""
        seen: dict[str, bool] = {}
        for name in self._all_names:
            if not name.startswith(prefix):
                continue
            rest = name[len(prefix) :]
            seg = rest.split("/")[0]
            if seg and seg not in seen:
                full = prefix + seg
                seen[seg] = any(n.startswith(full + "/") for n in self._all_names)
        return seen

    def _sort_key(self, seg: str, prefix: str) -> tuple[int, str]:
        """Sort priority path first, then alphabetically."""
        full = prefix + seg
        on_priority = full == self._priority_path or self._priority_path.startswith(
            full + "/"
        )
        return (0 if on_priority else 1, seg)

    def _leaf_entry(self, seg: str, full: str) -> Entry:
        """Build a leaf Entry with dim annotation label and optional default marker."""
        label = self._labels[full]
        marker = f" {DIM}(default){RESET}" if full == self._priority_path else ""
        return Entry(
            display=f"{seg} {DIM}{label}{RESET}{marker}",
            has_children=False,
            value=seg,
        )

    def __call__(self, path: str) -> list[Entry]:
        """Return entries for *path*, building the tree one level at a time."""
        prefix = (path + "/") if path else ""
        seen = self._segments(prefix)
        result: list[Entry] = []
        for seg in sorted(seen, key=lambda s: self._sort_key(s, prefix)):
            full = prefix + seg
            if seen[seg]:
                result.append(Entry(display=seg, has_children=True))
            else:
                result.append(self._leaf_entry(seg, full))
        return result


def tree_pick_from_names(
    labels: dict[str, str],
    title: str,
    *,
    priority_path: str = "",
    esc_label: str = "skip",
) -> str:  # pragma: no cover - interactive TTY only
    """Browse a flat dict of ``name → label`` as a tree and return the picked name.

    Names are split on ``/`` to form a navigable hierarchy.  Leaf nodes show
    their label as a dim annotation.  *priority_path* is sorted to the top.
    Returns ``""`` when the user presses Esc.
    """
    ls = _FlatNamesLs(labels, list(labels), priority_path)
    return tree_single_pick(ls, title, esc_label=esc_label)
