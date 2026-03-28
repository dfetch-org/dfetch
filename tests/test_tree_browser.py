# pyright: reportCallIssue=false
"""Hypothesis tests for the TreeBrowser state machine.

``TreeBrowser.run()`` is TTY-only and not exercised here.  Tests drive the
browser through :class:`_HeadlessBrowser`, a thin subclass that seeds state,
feeds keys, and exposes internal state — keeping all test-only scaffolding out
of the production class.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from dfetch.terminal.ansi import VIEWPORT
from dfetch.terminal.tree_browser import (
    BrowserConfig,
    TreeBrowser,
    TreeNode,
    all_descendants_deselected,
    deselected_paths,
)
from dfetch.terminal.types import Entry

settings.register_profile("ci", max_examples=30, deadline=None)
settings.register_profile("dev", max_examples=100, deadline=None)
settings.load_profile("dev")


# ---------------------------------------------------------------------------
# Headless test subclass — all test-only scaffolding lives here
# ---------------------------------------------------------------------------


class _HeadlessBrowser(TreeBrowser):
    """TreeBrowser subclass for headless testing.

    Adds :meth:`seed` and :meth:`feed_key` to drive the state machine
    without a TTY, and exposes :attr:`nodes`, :attr:`idx`, :attr:`top` so
    tests can inspect internal state.  Rendering (Screen / read_key) is
    never called.
    """

    def seed(self, nodes: list[TreeNode], *, idx: int = 0, top: int = 0) -> None:
        """Pre-load node state; clamp cursor and scroll to valid ranges."""
        self._nodes = list(nodes)
        self._idx = max(0, min(idx, len(nodes) - 1)) if nodes else 0
        self._top = top

    def feed_key(self, key: str) -> list[str] | None:
        """Process one keypress without rendering.

        Returns the selected-path list when the browser would exit, or
        ``None`` to continue.
        """
        if self._handle_nav(key):
            return None
        return self._handle_action(key)

    def adjust_scroll(self) -> None:
        """Expose the private scroll-adjustment for direct testing."""
        self._adjust_scroll()

    @property
    def idx(self) -> int:
        """Current cursor index."""
        return self._idx

    @property
    def top(self) -> int:
        """Current scroll offset."""
        return self._top


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_NAME = st.text(alphabet="abcdefghijklmnopqrstuvwxyz_", min_size=1, max_size=10)


@st.composite
def _node_st(draw, depth: int = 0) -> TreeNode:
    """Draw a single TreeNode at *depth*."""
    parts = [draw(_NAME) for _ in range(depth + 1)]
    return TreeNode(
        name=draw(_NAME),
        path="/".join(parts),
        is_dir=draw(st.booleans()),
        depth=depth,
        selected=draw(st.booleans()),
    )


@st.composite
def _node_list_st(draw, min_size: int = 1, max_size: int = 25) -> list[TreeNode]:
    """Draw a flat list of TreeNodes with arbitrary depths."""
    size = draw(st.integers(min_value=min_size, max_value=max_size))
    return [draw(_node_st(depth=draw(st.integers(0, 3)))) for _ in range(size)]


@st.composite
def _proper_tree_st(draw, _prefix: str = "", _depth: int = 0) -> list[TreeNode]:
    """Generate a pre-ordered node list with unique paths (parents before children).

    ``deselected_paths`` and ``all_descendants_deselected`` require this
    ordering; arbitrary flat lists are not valid input for those functions.
    """
    nodes: list[TreeNode] = []
    n = draw(st.integers(min_value=0 if _depth > 0 else 1, max_value=4))
    for i in range(n):
        name = f"{chr(97 + i)}{_depth}"  # a0, b0 … at depth 0; a1, b1 … at depth 1
        path = f"{_prefix}/{name}" if _prefix else name
        is_dir = draw(st.booleans()) if _depth < 2 else False
        selected = draw(st.booleans())
        nodes.append(
            TreeNode(
                name=name, path=path, is_dir=is_dir, depth=_depth, selected=selected
            )
        )
        if is_dir:
            nodes.extend(draw(_proper_tree_st(_prefix=path, _depth=_depth + 1)))
    return nodes


@st.composite
def _dir_with_children_st(
    draw,
) -> tuple[list[TreeNode], list[Entry]]:
    """Draw an unexpanded dir node at index 0, optional siblings, and a children spec."""
    dir_name = draw(_NAME)
    dir_node = TreeNode(name=dir_name, path=dir_name, is_dir=True, depth=0)
    siblings = draw(st.lists(_node_st(depth=0), min_size=0, max_size=5))

    child_names = draw(st.lists(_NAME, min_size=1, max_size=8))
    children: list[Entry] = [
        Entry(display=name, has_children=draw(st.booleans())) for name in child_names
    ]
    return [dir_node] + siblings, children


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

_NAV_KEYS = ["UP", "DOWN", "PGUP", "PGDN"]


def _browser(
    nodes: list[TreeNode],
    *,
    idx: int = 0,
    top: int = 0,
    config: BrowserConfig = BrowserConfig(),
    children: list[Entry] | None = None,
) -> _HeadlessBrowser:
    """Return a seeded _HeadlessBrowser backed by *children* (or empty) for expansions."""
    dir_path = nodes[0].path if nodes else ""
    ls = (
        (lambda path: children if path == dir_path else [])
        if children
        else (lambda _: [])
    )
    browser = _HeadlessBrowser(ls, "test", config)
    browser.seed(nodes, idx=idx, top=top)
    return browser


# ---------------------------------------------------------------------------
# Navigation — index invariants
# ---------------------------------------------------------------------------


@given(
    nodes=_node_list_st(),
    keys=st.lists(st.sampled_from(_NAV_KEYS), min_size=1, max_size=100),
    start=st.integers(min_value=0, max_value=24),
)
def test_navigation_index_stays_in_bounds(nodes, keys, start) -> None:
    """Cursor index must remain in [0, len-1] after any sequence of nav keys."""
    browser = _browser(nodes, idx=start)
    for key in keys:
        browser.feed_key(key)
    assert 0 <= browser.idx < len(browser.nodes)


@given(
    nodes=_node_list_st(),
    keys=st.lists(st.sampled_from(_NAV_KEYS), min_size=1, max_size=100),
    start=st.integers(min_value=0, max_value=24),
)
def test_navigation_never_mutates_node_list(nodes, keys, start) -> None:
    """Navigation keys must never add, remove or replace nodes."""
    browser = _browser(nodes, idx=start)
    snapshot = list(browser.nodes)
    for key in keys:
        browser.feed_key(key)
    assert browser.nodes == snapshot


@given(nodes=_node_list_st(min_size=2))
def test_down_then_up_returns_to_start(nodes) -> None:
    """DOWN then UP from index 0 must return to 0."""
    browser = _browser(nodes, idx=0)
    browser.feed_key("DOWN")
    browser.feed_key("UP")
    assert browser.idx == 0


@given(nodes=_node_list_st())
def test_down_from_last_node_stays(nodes) -> None:
    """DOWN from the last node must not move the cursor."""
    last = len(nodes) - 1
    browser = _browser(nodes, idx=last)
    browser.feed_key("DOWN")
    assert browser.idx == last


@given(nodes=_node_list_st())
def test_up_from_first_node_stays(nodes) -> None:
    """UP from the first node must not move the cursor."""
    browser = _browser(nodes, idx=0)
    browser.feed_key("UP")
    assert browser.idx == 0


# ---------------------------------------------------------------------------
# Scroll invariants
# ---------------------------------------------------------------------------


@given(
    nodes=_node_list_st(),
    idx=st.integers(min_value=0, max_value=24),
    top=st.integers(min_value=0, max_value=24),
)
def test_adjust_scroll_keeps_cursor_visible(nodes, idx, top) -> None:
    """After adjust_scroll the cursor must fall inside the viewport."""
    browser = _browser(nodes, idx=idx, top=top)
    browser.adjust_scroll()
    assert browser.top <= browser.idx < browser.top + VIEWPORT


@given(
    nodes=_node_list_st(),
    idx=st.integers(min_value=0, max_value=24),
    top=st.integers(min_value=0, max_value=24),
)
def test_adjust_scroll_top_is_nonnegative(nodes, idx, top) -> None:
    """adjust_scroll must never produce a negative scroll offset."""
    browser = _browser(nodes, idx=idx, top=top)
    browser.adjust_scroll()
    assert browser.top >= 0


# ---------------------------------------------------------------------------
# Expand / collapse symmetry
# ---------------------------------------------------------------------------


@given(spec=_dir_with_children_st())
def test_expand_increases_count_by_children(spec) -> None:
    """Expanding a dir must add exactly len(children) nodes."""
    nodes, children = spec
    original = len(nodes)
    browser = _browser(nodes, children=children)
    browser.feed_key("RIGHT")
    assert len(browser.nodes) == original + len(children)


@given(spec=_dir_with_children_st())
def test_expand_sets_expanded_flag(spec) -> None:
    """After RIGHT the node's expanded flag must be True."""
    nodes, children = spec
    browser = _browser(nodes, children=children)
    browser.feed_key("RIGHT")
    assert browser.nodes[0].expanded


@given(spec=_dir_with_children_st())
def test_expand_then_collapse_restores_count(spec) -> None:
    """RIGHT then LEFT on the same dir must restore the original node count."""
    nodes, children = spec
    original = len(nodes)
    browser = _browser(nodes, children=children)
    browser.feed_key("RIGHT")  # expand
    browser.feed_key("LEFT")  # collapse (cursor stays at 0, which is an expanded dir)
    assert len(browser.nodes) == original


@given(spec=_dir_with_children_st())
def test_collapse_clears_expanded_flag(spec) -> None:
    """After RIGHT then LEFT the node's expanded flag must be False."""
    nodes, children = spec
    browser = _browser(nodes, children=children)
    browser.feed_key("RIGHT")
    browser.feed_key("LEFT")
    assert not browser.nodes[0].expanded


@given(spec=_dir_with_children_st())
def test_second_expand_does_not_duplicate_children(spec) -> None:
    """RIGHT → LEFT → RIGHT must not duplicate children."""
    nodes, children = spec
    original = len(nodes)
    browser = _browser(nodes, children=children)
    browser.feed_key("RIGHT")
    browser.feed_key("LEFT")
    browser.feed_key("RIGHT")
    assert len(browser.nodes) == original + len(children)


# ---------------------------------------------------------------------------
# Cascade selection (multi mode, SPACE on dir)
# ---------------------------------------------------------------------------


@given(spec=_dir_with_children_st())
def test_space_in_multi_mode_cascades_to_all_children(spec) -> None:
    """SPACE on an expanded dir in multi mode must set all children to the same value."""
    nodes, children = spec
    browser = _browser(nodes, children=children, config=BrowserConfig(multi=True))
    browser.feed_key("RIGHT")  # expand
    browser.feed_key("SPACE")  # toggle + cascade
    parent = browser.nodes[0]
    for node in browser.nodes[1:]:
        if node.depth <= parent.depth:
            break
        assert node.selected == parent.selected


@given(spec=_dir_with_children_st())
def test_all_descendants_deselected_after_cascade_false(spec) -> None:
    """all_descendants_deselected must be True after cascading False to all children."""
    nodes, children = spec
    # Force the dir to start selected so SPACE sets it (and children) to False.
    nodes[0].selected = True
    browser = _browser(nodes, children=children, config=BrowserConfig(multi=True))
    browser.feed_key("RIGHT")  # expand
    browser.feed_key("SPACE")  # toggle: True → False, cascade False
    assert all_descendants_deselected(browser.nodes, 0)


@given(spec=_dir_with_children_st())
def test_not_all_descendants_deselected_after_cascade_true(spec) -> None:
    """all_descendants_deselected must be False after cascading True (children exist)."""
    nodes, children = spec
    # Force the dir to start deselected so SPACE sets it (and children) to True.
    nodes[0].selected = False
    browser = _browser(nodes, children=children, config=BrowserConfig(multi=True))
    browser.feed_key("RIGHT")  # expand
    browser.feed_key("SPACE")  # toggle: False → True, cascade True
    assert not all_descendants_deselected(browser.nodes, 0)


# ---------------------------------------------------------------------------
# deselected_paths (requires properly-ordered trees)
# ---------------------------------------------------------------------------


@given(nodes=_proper_tree_st())
def test_deselected_paths_empty_when_all_selected(nodes) -> None:
    """deselected_paths must return [] when every node is selected."""
    for node in nodes:
        node.selected = True
    assert not deselected_paths(nodes)


@given(nodes=_proper_tree_st())
def test_deselected_paths_only_references_deselected_nodes(nodes) -> None:
    """Every path returned by deselected_paths must belong to a deselected node."""
    deselected_node_paths = {n.path for n in nodes if not n.selected}
    for path in deselected_paths(nodes):
        assert path in deselected_node_paths


@given(nodes=_proper_tree_st())
def test_deselected_paths_are_prefix_free(nodes) -> None:
    """No returned path should be a directory-prefix of another returned path."""
    paths = deselected_paths(nodes)
    for i, a in enumerate(paths):
        for j, b in enumerate(paths):
            if i != j:
                assert not b.startswith(a + "/"), f"{a!r} is a prefix of {b!r}"


# ---------------------------------------------------------------------------
# Key action handlers
# ---------------------------------------------------------------------------


@given(nodes=_node_list_st())
def test_esc_always_returns_empty_list(nodes) -> None:
    """ESC must return [] regardless of cursor position or node state."""
    assert _browser(nodes).feed_key("ESC") == []


@given(nodes=_node_list_st())
def test_unknown_key_returns_none(nodes) -> None:
    """An unrecognised key must return None (keep the loop running)."""
    assert _browser(nodes).feed_key("__NO_SUCH_KEY__") is None


@given(nodes=_node_list_st(), idx=st.integers(min_value=0, max_value=24))
def test_enter_on_leaf_single_mode_returns_its_path(nodes, idx) -> None:
    """ENTER on a leaf in single-select mode must return exactly that node's path."""
    leaf_indices = [i for i, n in enumerate(nodes) if not n.is_dir]
    if not leaf_indices:
        return
    i = leaf_indices[idx % len(leaf_indices)]
    browser = _browser(nodes, idx=i, config=BrowserConfig(multi=False))
    assert browser.feed_key("ENTER") == [nodes[i].path]


@given(nodes=_node_list_st())
def test_enter_in_multi_mode_returns_all_selected_paths(nodes) -> None:
    """ENTER in multi-select mode must return exactly the paths of selected nodes."""
    browser = _browser(nodes, config=BrowserConfig(multi=True))
    expected = [n.path for n in nodes if n.selected]
    assert browser.feed_key("ENTER") == expected


@given(
    nodes=_node_list_st(),
    keys=st.lists(
        st.sampled_from([*_NAV_KEYS, "LEFT", "RIGHT", "ESC", "ENTER", "SPACE"]),
        min_size=1,
        max_size=50,
    ),
    start=st.integers(min_value=0, max_value=24),
)
def test_any_key_sequence_never_raises(nodes, keys, start) -> None:
    """No key combination on any tree should raise an exception."""
    browser = _browser(nodes, idx=start)
    for key in keys:
        result = browser.feed_key(key)
        if result is not None:
            break  # ESC or selection — browser would exit here
