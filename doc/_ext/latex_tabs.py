"""PDF/LaTeX rendering for sphinx-tabs directives.

sphinx-tabs only registers HTML visitors for its custom node types.  For all
other builders it falls back to plain ``nodes.container`` nodes, so the tab
labels render as unstyled text with no visual separation between variants.

This extension inserts a ``SphinxTransform`` (LaTeX/rinoh builds only) that
rewrites the generic container tree produced by sphinx-tabs into custom
``LatexTabsGroup`` / ``LatexTabEntry`` nodes, and registers LaTeX visitors
that render each tab as an unnumbered subsection heading followed by its
content.

Expected result in PDF::

    Linux
    ─────
    content …

    macOS
    ─────
    content …

    Windows
    ───────
    content …
"""

import re

from docutils import nodes
from sphinx.transforms import SphinxTransform

# ---------------------------------------------------------------------------
# Custom node types
# ---------------------------------------------------------------------------


class LatexTabsGroup(nodes.General, nodes.Element):
    """Outer wrapper replacing a ``sphinx-tabs`` container in LaTeX output."""


class LatexTabEntry(nodes.General, nodes.Element):
    """One tab (label + content) inside a ``LatexTabsGroup``."""


# ---------------------------------------------------------------------------
# Transform: rewrite sphinx-tabs containers for LaTeX
# ---------------------------------------------------------------------------

_LATEX_SPECIAL = re.compile(r"([&%$#_{}~^\\])")


def _escape_latex(text: str) -> str:
    return _LATEX_SPECIAL.sub(lambda m: "\\" + m.group(1), text)


class LatexTabsTransform(SphinxTransform):
    """Convert sphinx-tabs containers into styled LatexTabsGroup nodes.

    Only runs for latex/rinoh builders.  The sphinx-tabs fallback structure
    for non-HTML builders is::

        nodes.container [classes: ['sphinx-tabs']]
          nodes.container  (outer per tab)
            nodes.container  (tab — holds the label)
            nodes.container  (panel — holds the content)

    This transform converts that into::

        LatexTabsGroup
          LatexTabEntry [label="Git"]
            <panel content nodes>
          LatexTabEntry [label="SVN"]
            <panel content nodes>
          …
    """

    default_priority = 500

    def apply(self, **kwargs) -> None:
        if self.app.builder.name not in ("latex", "rinoh"):
            return

        for tabs_node in self.document.traverse(
            lambda n: isinstance(n, nodes.container)
            and "sphinx-tabs" in n.get("classes", [])
        ):
            group = LatexTabsGroup()
            for outer in list(tabs_node.children):
                if not isinstance(outer, nodes.container) or len(outer.children) < 2:
                    continue
                tab_container = outer.children[0]
                panel = outer.children[1]

                entry = LatexTabEntry()
                entry["label"] = tab_container.astext().strip()
                entry += list(panel.children)
                group += entry

            tabs_node.replace_self(group)


# ---------------------------------------------------------------------------
# LaTeX visitors
# ---------------------------------------------------------------------------


def visit_latex_tabs_group(_translator, _node) -> None:
    """No-op: subsection headings on each entry provide all needed structure."""


def depart_latex_tabs_group(_translator, _node) -> None:
    """No-op: nothing to emit after the last tab entry."""


def visit_latex_tab_entry(translator, node) -> None:
    """Emit an unnumbered subsubsection heading before the tab content."""
    label = _escape_latex(node["label"])
    translator.body.append(f"\n\\subsubsection*{{{label}}}\n")


def depart_latex_tab_entry(_translator, _node) -> None:
    """No-op: the next subsubsection heading provides the visual separation."""


def _html_skip(translator, node) -> None:
    raise nodes.SkipNode


# ---------------------------------------------------------------------------
# Extension setup
# ---------------------------------------------------------------------------


def setup(app):
    """Register nodes, visitors, and the LaTeX transform."""
    app.add_node(
        LatexTabsGroup,
        latex=(visit_latex_tabs_group, depart_latex_tabs_group),
        html=(_html_skip, None),
    )
    app.add_node(
        LatexTabEntry,
        latex=(visit_latex_tab_entry, depart_latex_tab_entry),
        html=(_html_skip, None),
    )
    app.add_transform(LatexTabsTransform)

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
