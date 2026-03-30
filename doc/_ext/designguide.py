"""Sphinx directives ``palette`` and ``swatch`` for design-guide colour palettes.

Renders design-guide colour palette HTML without raw HTML blocks.

Usage::

    .. palette::

       .. swatch:: #c2620a
          :token: --primary
          :label: Amber Orange
          :usage: CTAs, active borders, diagram start nodes, section pips

    .. palette::
       :columns: 4

       .. swatch:: #c2620a
          :token: --dxt-tutorial
          :label: Tutorials
          :usage: Same as ``--primary``; warm amber for learning-oriented pages

Register in conf.py::

    extensions = [..., "designguide"]
"""

import html
from typing import Any

from docutils import nodes
from docutils.nodes import Node
from docutils.parsers.rst import Directive, directives
from sphinx.application import Sphinx


class SwatchDirective(Directive):
    """Render a single colour swatch card as ``.. swatch:: #hexcolor``."""

    required_arguments = 1
    optional_arguments = 0
    option_spec = {
        "token": directives.unchanged,
        "label": directives.unchanged,
        "usage": directives.unchanged,
        "border": directives.unchanged,
    }
    has_content = False

    def run(self) -> list[Node]:
        """Emit a ``dg-swatch`` HTML block for the given colour.

        Returns:
            A list containing a single raw HTML node.
        """
        color = html.escape(self.arguments[0].strip(), quote=True)
        token = html.escape(self.options.get("token", ""))
        label = html.escape(self.options.get("label", ""))
        usage = html.escape(self.options.get("usage", ""))
        border = html.escape(self.options.get("border", ""), quote=True)

        color_style = f"background:{color};"
        if border:
            color_style += f" border-bottom:1px solid {border};"

        markup = (
            f'<div class="dg-swatch">'
            f'<div class="dg-swatch-color" style="{color_style}"></div>'
            f'<div class="dg-swatch-body">'
            f'<div class="dg-swatch-token">{token}</div>'
            f'<div class="dg-swatch-hex">{color}</div>'
            f'<div class="dg-swatch-label">{label}</div>'
            f'<div class="dg-swatch-usage">{usage}</div>'
            f"</div>"
            f"</div>"
        )
        return [nodes.raw("", markup, format="html")]


class PaletteDirective(Directive):
    """Render a grid of ``.. swatch::`` directives as ``.. palette::``."""

    required_arguments = 0
    optional_arguments = 0
    option_spec = {
        "columns": directives.positive_int,
    }
    has_content = True

    def run(self) -> list[Node]:
        """Emit a ``dg-palette`` wrapper div containing parsed swatch children.

        Returns:
            A list of nodes: opening div, swatch children, closing div.
        """
        columns: int | None = self.options.get("columns", None)

        style = ""
        if columns:
            style = f' style="grid-template-columns:repeat({columns},1fr);"'

        open_div = nodes.raw("", f'<div class="dg-palette"{style}>\n', format="html")
        close_div = nodes.raw("", "</div>\n", format="html")

        container = nodes.section()
        container.document = self.state.document
        self.state.nested_parse(self.content, self.content_offset, container)

        return [open_div, *container.children, close_div]


def setup(app: Sphinx) -> dict[str, Any]:
    """Register the ``palette`` and ``swatch`` directives with Sphinx.

    Args:
        app: The Sphinx application object.

    Returns:
        Extension metadata dictionary.
    """
    app.add_directive("palette", PaletteDirective)
    app.add_directive("swatch", SwatchDirective)
    return {"version": "0.1", "parallel_read_safe": True, "parallel_write_safe": True}
