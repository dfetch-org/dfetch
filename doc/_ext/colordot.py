"""Sphinx role ``colordot`` for inline colour swatches.

Renders an inline ``<span class="dg-dot" style="background:<color>;"></span>``
so RST tables can show a filled colour circle next to a hex value without
resorting to raw HTML blocks.

Usage in .rst files::

    :colordot:`#c2620a` ``#c2620a`` (``--primary``)

Register in conf.py::

    extensions = [..., "colordot"]
"""

from typing import Any

from docutils import nodes
from docutils.nodes import Node, system_message
from sphinx.application import Sphinx


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
    color = text.strip()
    html = f'<span class="dg-dot" style="background:{color};"></span>'
    node = nodes.raw("", html, format="html")
    return [node], []


def setup(app: Sphinx) -> dict[str, Any]:
    """Register the ``colordot`` role with Sphinx.

    Args:
        app: The Sphinx application object.

    Returns:
        Extension metadata dictionary.
    """
    app.add_role("colordot", colordot_role)
    return {"version": "0.1", "parallel_read_safe": True, "parallel_write_safe": True}
