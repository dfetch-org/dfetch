"""Sphinx extension that makes section IDs unique across a document.

sphinx-argparse generates identical section IDs (e.g.
``dfetch.__main__-create_parser-positional-arguments``) for every subcommand
because they all share the same argparse function.  The extension's own
``ensure_unique_ids`` helper only deduplicates within a single directive call,
so IDs remain duplicate across subcommand blocks.  These duplicates produce
``multiply-defined label`` warnings in the LaTeX output.

This extension runs a second deduplication pass over the fully-resolved
doctree, appending ``_repeat1``, ``_repeat2``, … suffixes to any duplicate IDs
that survive after sphinx-argparse's own pass.

Register in ``conf.py``::

    extensions = [..., "unique_section_ids"]
"""

from typing import Any

from docutils import nodes
from sphinx.application import Sphinx


def _deduplicate_ids(_app: Sphinx, doctree: nodes.document, _fromdocname: str) -> None:
    """Rename duplicate section IDs within a resolved doctree.

    Traverses every ``section`` node in *doctree* and ensures each ID is
    unique.  When a collision is detected the duplicate receives a
    ``_repeat<n>`` suffix (incrementing *n* until the result is free), which
    mirrors the strategy used by sphinx-argparse's own ``ensure_unique_ids``
    helper but applies it document-wide rather than per-directive.

    Args:
        _app: The Sphinx application object (unused).
        doctree: The fully-resolved document tree being processed.
        _fromdocname: The document name that produced the tree (unused).
    """
    seen: set[str] = set()
    for node in doctree.traverse(nodes.section):
        new_ids: list[str] = []
        for id_ in node["ids"]:
            if id_ not in seen:
                seen.add(id_)
                new_ids.append(id_)
            else:
                counter = 1
                while f"{id_}_repeat{counter}" in seen:
                    counter += 1
                unique_id = f"{id_}_repeat{counter}"
                seen.add(unique_id)
                new_ids.append(unique_id)
        node["ids"] = new_ids


def setup(app: Sphinx) -> dict[str, Any]:
    """Register the section-ID deduplication handler with Sphinx.

    Args:
        app: The Sphinx application object.

    Returns:
        Extension metadata dictionary.
    """
    app.connect("doctree-resolved", _deduplicate_ids)
    return {"version": "0.1", "parallel_read_safe": True}
