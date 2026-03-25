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
        """Current node list (populated after :meth:`run` or :meth:`seed`)."""
        return self._nodes

    @property
    def idx(self) -> int:
        """Current cursor index."""
        return self._idx

    @property
    def top(self) -> int:
        """Current scroll offset (index of the topmost visible node)."""
        return self._top

    def seed(self, nodes: list[TreeNode], *, idx: int = 0, top: int = 0) -> None:
        """Pre-load node state without running the TTY loop.

        Intended for headless driving and unit tests.  Cursor and scroll are
        clamped to valid ranges automatically.
        """
        self._nodes = list(nodes)
        self._idx = max(0, min(idx, len(nodes) - 1)) if nodes else 0
        self._top = top

    def feed_key(self, key: str) -> list[str] | None:
        """Process one keypress without rendering.

        Returns the selected-path list when the browser would exit (an empty
        list for ESC/skip), or ``None`` to indicate the loop should continue.
        Intended for headless driving and unit tests.
        """
        if self._handle_nav(key):
            return None
        return self._handle_action(key)

    def adjust_scroll(self) -> None:
        """Ensure the cursor index is within the visible viewport."""
        if self._idx < self._top:
            self._top = self._idx
        elif self._idx >= self._top + VIEWPORT:
            self._top = self._idx - VIEWPORT + 1

    # ------------------------------------------------------------------
    # Node mutation
    # ------------------------------------------------------------------

    def _expand(self, idx: int) -> None:
        """Expand the directory node at *idx*, loading children if needed."""
        node = self._nodes[idx]
        if not node.children_loaded:
            children = [
                TreeNode(
                    name=name,
                    path=f"{node.path}/{strip_ansi(name)}",
                    is_dir=is_dir,
                    depth=node.depth + 1,
                    selected=node.selected,
                )
                for name, is_dir in self._ls_function(node.path)
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

    def _render_lines(self) -> list[str]:
        """Build display strings for the visible viewport slice."""
        lines: list[str] = []
        for i in range(self._top, min(self._top + VIEWPORT, len(self._nodes))):
            node = self._nodes[i]
            indent = "  " * node.depth
            icon = ("▾ " if node.expanded else "▸ ") if node.is_dir else "  "
            cursor = f"{GREEN}▶{RESET}" if i == self._idx else " "
            if self._config.multi:
                name = f"{DIM}{node.name}{RESET}" if not node.selected else node.name
                lines.append(f"  {cursor} {indent}{icon}{name}")
            else:
                check = f"{GREEN}✓ {RESET}" if node.selected else "  "
                name = f"{BOLD}{node.name}{RESET}" if i == self._idx else node.name
                lines.append(f"  {cursor} {check}{indent}{icon}{name}")
        return lines

    def _build_frame(self) -> list[str]:
        """Build all display lines for one render frame."""
        n = len(self._nodes)
        header = [f"  {GREEN}?{RESET} {BOLD}{self._title}:{RESET}"]
        if self._top > 0:
            header.append(f"    {DIM}↑ {self._top} more above{RESET}")
        footer: list[str] = []
        remaining = n - (self._top + VIEWPORT)
        if remaining > 0:
            footer.append(f"    {DIM}↓ {remaining} more below{RESET}")
        footer.append(f"  {DIM}{self._nav_hint()}{RESET}")
        return header + self._render_lines() + footer

    # ------------------------------------------------------------------
    # Scroll helpers
    # ------------------------------------------------------------------

    def _nudge_scroll_after_expand(self) -> None:
        """Scroll down 1 when a just-expanded dir sits at the viewport bottom."""
        node = self._nodes[self._idx]
        if (
            node.is_dir
            and node.expanded
            and self._idx == self._top + VIEWPORT - 1
            and self._idx + 1 < len(self._nodes)
        ):
            self._top += 1

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

    def _handle_action(self, key: str) -> list[str] | None:
        """Dispatch a non-navigation keypress; return a result list or None to continue."""
        node = self._nodes[self._idx]
        if key == "RIGHT":
            if node.is_dir and not node.expanded:
                self._expand(self._idx)
        elif key == "LEFT":
            self._handle_left()
        elif key == "SPACE":
            return (
                self._handle_enter()
                if not self._config.multi and node.is_dir
                else self._handle_space()
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
                name=name,
                path=strip_ansi(name),
                is_dir=is_dir,
                depth=0,
                selected=self._config.all_selected,
            )
            for name, is_dir in root_entries
        ]
        screen = Screen()

        while True:
            if not self._nodes:
                screen.clear()
                return []
            self._idx = max(0, min(self._idx, len(self._nodes) - 1))
            self.adjust_scroll()
            screen.draw(self._build_frame())
            key = read_key()

            if self._handle_nav(key):
                continue

            result = self._handle_action(key)
            if result is not None:
                screen.clear()
                return result
            self._nudge_scroll_after_expand()


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
) -> str:
    """Browse a remote tree and return a single selected path (``""`` on skip)."""
    config = BrowserConfig(dirs_selectable=dirs_selectable, esc_label=esc_label)
    browser = TreeBrowser(ls_function, title, config)
    result = browser.run()
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
