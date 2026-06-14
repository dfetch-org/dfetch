"""Sphinx extension for inline colour swatches and PDF emoji substitution.

The ``:colordot:`` role renders a filled colour circle as a CSS ``<span>``
in HTML builds.

For PDF/LaTeX builds this extension also replaces the coloured-circle emoji
used as severity/risk badges in the threat-model tables with equivalent
TikZ-drawn circles.  The body font (TeX Gyre Heroes) has no glyphs for these
supplementary-plane code points so without this replacement XeLaTeX silently
drops them.

Usage in .rst files::

    :colordot:`#c2620a` ``#c2620a`` (``--primary``)

Register in conf.py::

    extensions = [..., "colordot"]
"""

import html
import re
from typing import Any, List

from docutils import nodes
from docutils.nodes import Node, system_message
from sphinx.application import Sphinx

# ---------------------------------------------------------------------------
# :colordot: role — HTML colour swatch
# ---------------------------------------------------------------------------


def colordot_role(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    name: str,  # pylint: disable=unused-argument
    rawtext: str,  # pylint: disable=unused-argument
    text: str,
    lineno: int,  # pylint: disable=unused-argument
    inliner: Any,  # pylint: disable=unused-argument
    options: dict[str, Any] | None = None,  # pylint: disable=unused-argument
    content: list[str] | None = None,  # pylint: disable=unused-argument
) -> tuple[list[Node], list[system_message]]:
    """Render a filled colour circle as an inline HTML ``<span>``.

    Args:
        name: The role name (``colordot``).
        rawtext: The raw markup including role and argument.
        text: The interpreted text (a CSS colour value, e.g. ``#c2620a``).
        lineno: The line number in the source document.
        inliner: The inliner instance.
        options: Directive options mapping.
        content: The directive content lines.

    Returns:
        A two-tuple of (node list, system message list) as required by Sphinx.
    """
    color = html.escape(text.strip(), quote=True)
    markup = f'<span class="dg-dot" style="background:{color};"></span>'
    node = nodes.raw("", markup, format="html")
    return [node], []


# ---------------------------------------------------------------------------
# Emoji → LaTeX replacement for PDF builds
# ---------------------------------------------------------------------------

# Coloured-circle emoji used as severity/risk badges in the threat-model
# tables.  Map each code point to a TikZ fill command that produces a
# matching coloured disc in XeLaTeX output.
_EMOJI_LATEX: dict[str, str] = {
    "\U0001f7e2": r"\,\tikz[baseline=-0.5ex]{\fill[green!70!black](0,0)circle(0.45ex);}\,",  # 🟢
    "\U0001f7e1": r"\,\tikz[baseline=-0.5ex]{\fill[yellow!70!black](0,0)circle(0.45ex);}\,",  # 🟡
    "\U0001f7e0": r"\,\tikz[baseline=-0.5ex]{\fill[orange!90!black](0,0)circle(0.45ex);}\,",  # 🟠
    "\U0001f534": r"\,\tikz[baseline=-0.5ex]{\fill[red!70!black](0,0)circle(0.45ex);}\,",  # 🔴
}

_EMOJI_RE = re.compile("|".join(re.escape(c) for c in _EMOJI_LATEX))


def _replace_emoji_for_latex(
    app: Sphinx,
    doctree: nodes.document,
    fromdocname: str,  # pylint: disable=unused-argument
) -> None:
    """Replace coloured-circle emoji with TikZ circles in LaTeX/PDF builds.

    Args:
        app: The Sphinx application object.
        doctree: The resolved document tree being processed.
        fromdocname: The source document name (unused).
    """
    if app.builder.name not in ("latex", "rinoh"):
        return

    targets = [n for n in doctree.traverse(nodes.Text) if _EMOJI_RE.search(str(n))]
    for text_node in targets:
        text = str(text_node)
        parent = text_node.parent
        if parent is None:
            continue
        idx = parent.children.index(text_node)
        new_nodes: List[Node] = []
        last = 0
        for m in _EMOJI_RE.finditer(text):
            if m.start() > last:
                new_nodes.append(nodes.Text(text[last : m.start()]))
            raw = nodes.raw("", _EMOJI_LATEX[m.group()], format="latex")
            raw.parent = parent
            new_nodes.append(raw)
            last = m.end()
        if last < len(text):
            new_nodes.append(nodes.Text(text[last:]))
        parent.children[idx : idx + 1] = new_nodes


# ---------------------------------------------------------------------------
# Sphinx extension setup
# ---------------------------------------------------------------------------


def setup(app: Sphinx) -> dict[str, Any]:
    """Register the ``colordot`` role and PDF emoji handler with Sphinx.

    Args:
        app: The Sphinx application object.

    Returns:
        Extension metadata dictionary.
    """
    app.add_role("colordot", colordot_role)
    app.connect("doctree-resolved", _replace_emoji_for_latex)
    return {"version": "0.2", "parallel_read_safe": True, "parallel_write_safe": True}
