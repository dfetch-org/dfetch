"""
Custom Sphinx directive for including Gherkin scenarios from feature files.

Usage in conf.py:

    extensions = ["scenario_directive"]

Usage in .rst files:

    .. scenario-include:: ../features/fetch-git-repo.feature
       :scenario:
          Scenario Title 1
          Scenario Title 2

If ``:scenario:`` is omitted, all scenarios in the feature file are included.

**PDF / LaTeX builds** automatically move scenarios to an appendix grouped by
the behave command-tag (``@update``, ``@check``, …) that was placed on the
feature file.  The directive's original location receives a cross-reference to
the appendix entry instead.

Use the ``:inline:`` flag to keep a specific inclusion in place even when
building a PDF:

    .. scenario-include:: ../features/fetch-git-repo.feature
       :inline:

The appendix itself is rendered by placing the companion directive anywhere in
the document tree:

    .. scenario-appendix::

Behave tags treated as *command tags* map to the appendix sections.  Any tag
that appears in ``_NON_COMMAND_TAGS`` (e.g. ``remote-svn``) is ignored when
determining the command tag.
"""

import html
import os
import re
from typing import Dict, List, Optional, Tuple

from docutils import nodes
from docutils.parsers.rst import Directive, directives
from docutils.statemachine import StringList


# ---------------------------------------------------------------------------
# Tags that are NOT command-name tags (infrastructure / skip markers).
# ---------------------------------------------------------------------------
_NON_COMMAND_TAGS = {"remote-svn"}

# Human-readable section titles for each command tag.
_TAG_LABELS: Dict[str, str] = {
    "update": "``dfetch update`` scenarios",
    "check": "``dfetch check`` scenarios",
    "add": "``dfetch add`` scenarios",
    "remove": "``dfetch remove`` scenarios",
    "diff": "``dfetch diff`` scenarios",
    "update-patch": "``dfetch update-patch`` scenarios",
    "format-patch": "``dfetch format-patch`` scenarios",
    "freeze": "``dfetch freeze`` scenarios",
    "import": "``dfetch import`` scenarios",
    "report": "``dfetch report`` scenarios",
    "validate": "``dfetch validate`` scenarios",
}

# Canonical display order for command tags in the appendix.
_TAG_ORDER = [
    "update",
    "check",
    "add",
    "remove",
    "diff",
    "update-patch",
    "format-patch",
    "freeze",
    "import",
    "report",
    "validate",
]


# ---------------------------------------------------------------------------
# Custom node types
# ---------------------------------------------------------------------------


class scenario_appendix_placeholder(nodes.General, nodes.Element):
    """Replaced by the full appendix content during the resolve phase."""


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _feature_tags(feature_path: str) -> List[str]:
    """Return all behave tags declared before the ``Feature:`` line."""
    tags: List[str] = []
    with open(feature_path, encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if stripped.startswith("Feature:"):
                break
            if stripped.startswith("@"):
                tags.extend(t.lstrip("@") for t in stripped.split())
    return tags


def _command_tag(feature_path: str) -> str:
    """Return the first non-infrastructure tag from the feature file, or 'other'."""
    for tag in _feature_tags(feature_path):
        if tag not in _NON_COMMAND_TAGS:
            return tag
    return "other"


def _feature_title(feature_path: str) -> str:
    """Return the text after ``Feature:`` in the feature file."""
    with open(feature_path, encoding="utf-8") as fh:
        for line in fh:
            match = re.match(r"^\s*Feature:\s*(.+)$", line)
            if match:
                return match.group(1).strip()
    return os.path.basename(feature_path)


def _all_scenarios(feature_path: str) -> Tuple[str, ...]:
    """Return all scenario titles in the feature file (preserves order)."""
    with open(feature_path, encoding="utf-8") as fh:
        return tuple(
            re.findall(
                r"^\s*Scenario(?:\s+Outline)?:\s*(.+)$", fh.read(), re.MULTILINE
            )
        )


def _full_feature_content(feature_path: str) -> str:
    """Return the complete textual content of a feature file."""
    with open(feature_path, encoding="utf-8") as fh:
        return fh.read()


# ---------------------------------------------------------------------------
# scenario-include directive
# ---------------------------------------------------------------------------


class ScenarioIncludeDirective(Directive):
    """Include Gherkin scenarios from a feature file.

    In PDF/LaTeX builds the scenarios are moved to a dedicated appendix and
    replaced inline by a cross-reference, unless ``:inline:`` is given.
    """

    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {
        "scenario": str,
        "inline": directives.flag,  # keep inline even in PDF mode
    }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_pdf(self) -> bool:
        env = self.state.document.settings.env
        return env.app.builder.name in ("latex", "rinoh")

    def _feature_abs(self, feature_file: str) -> str:
        env = self.state.document.settings.env
        path = os.path.abspath(os.path.join(env.app.srcdir, feature_file))
        if not os.path.exists(path):
            raise self.error(f"Feature file not found: {path}")
        return path

    def _include_path(self, feature_abs: str) -> str:
        """Path for literalinclude, relative to the current RST document."""
        env = self.state.document.settings.env
        current_doc_dir = os.path.dirname(
            os.path.join(env.app.srcdir, env.docname)
        )
        return os.path.relpath(feature_abs, current_doc_dir)

    def _requested_scenarios(
        self, available: Tuple[str, ...]
    ) -> List[str]:
        return [
            t.strip()
            for t in self.options.get("scenario", "").splitlines()
            if t.strip()
        ] or list(available)

    # ------------------------------------------------------------------
    # HTML / inline rendering (original behaviour)
    # ------------------------------------------------------------------

    def _render_html(
        self,
        include_path: str,
        feature_file: str,
        scenario_titles: List[str],
        available: Tuple[str, ...],
    ) -> List[nodes.Node]:
        container = nodes.section()
        for title in scenario_titles:
            end_before = (
                ":end-before: Scenario:"
                if title != available[-1]
                else ""
            )
            directive_rst = f"""
.. raw:: html

   <details>
   <summary><strong>Example</strong>: {html.escape(title)}</summary>

.. literalinclude:: {include_path}
    :language: gherkin
    :caption: {feature_file}
    :force:
    :dedent:
    :start-after: Scenario: {title}
    {end_before}

.. raw:: html

   </details>
"""
            viewlist = StringList()
            for i, line in enumerate(directive_rst.splitlines()):
                viewlist.append(line, source=f"<{self.name} directive>", offset=i)
            self.state.nested_parse(viewlist, self.content_offset, container)
        return container.children

    # ------------------------------------------------------------------
    # PDF rendering: register for appendix, return cross-reference
    # ------------------------------------------------------------------

    def _render_pdf(
        self,
        feature_file: str,
        feature_abs: str,
        scenario_titles: List[str],
    ) -> List[nodes.Node]:
        env = self.state.document.settings.env
        basename = os.path.splitext(os.path.basename(feature_abs))[0]
        label = f"appendix-{basename}"
        tag = _command_tag(feature_abs)
        title = _feature_title(feature_abs)

        # ----------------------------------------------------------
        # Store entry so the appendix directive can render it later.
        # The dict is keyed by absolute path to deduplicate across
        # multiple RST files that reference the same feature.
        # ----------------------------------------------------------
        if not hasattr(env, "scenario_appendix_entries"):
            env.scenario_appendix_entries = {}

        if feature_abs not in env.scenario_appendix_entries:
            env.scenario_appendix_entries[feature_abs] = {
                "feature_file": feature_file,
                "feature_abs": feature_abs,
                "feature_title": title,
                "command_tag": tag,
                "label": label,
                "source_doc": env.docname,
                "scenarios": list(scenario_titles),
            }
        else:
            existing = env.scenario_appendix_entries[feature_abs]
            for s in scenario_titles:
                if s not in existing["scenarios"]:
                    existing["scenarios"].append(s)

        # ----------------------------------------------------------
        # Return a short paragraph pointing to the appendix.
        # nodes.reference(internal=True, refid=...) produces a
        # \hyperref in LaTeX, which works within one compiled PDF.
        # ----------------------------------------------------------
        para = nodes.paragraph()
        para += nodes.emphasis(text="Scenarios: see ")
        ref = nodes.reference("", title, internal=True, refid=label)
        para += ref
        para += nodes.emphasis(text=" in the appendix.")
        return [para]

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def run(self) -> List[nodes.Node]:
        feature_file = self.arguments[0].strip()
        feature_abs = self._feature_abs(feature_file)
        available = _all_scenarios(feature_abs)
        scenario_titles = self._requested_scenarios(available)

        if self._is_pdf() and "inline" not in self.options:
            return self._render_pdf(feature_file, feature_abs, scenario_titles)

        return self._render_html(
            self._include_path(feature_abs),
            feature_file,
            scenario_titles,
            available,
        )


# ---------------------------------------------------------------------------
# scenario-appendix directive
# ---------------------------------------------------------------------------


class ScenarioAppendixDirective(Directive):
    """Render the appendix of all PDF-deferred scenarios.

    Place this directive once in the document (typically in an appendix
    page).  During the write phase it is replaced by sections grouped by
    command tag, containing the full content of each referenced feature file.

    In HTML builds scenarios appear inline in the main text, so this
    directive emits an explanatory note instead.
    """

    required_arguments = 0
    optional_arguments = 0
    has_content = False

    def run(self) -> List[nodes.Node]:
        env = self.state.document.settings.env
        if env.app.builder.name not in ("latex", "rinoh"):
            # HTML: scenarios are inline; provide a brief orientation note.
            note = nodes.note()
            para = nodes.paragraph()
            para += nodes.Text(
                "In the HTML edition, feature scenarios appear as expandable "
                "examples directly within each guide section. "
                "In the PDF edition they are collected here, grouped by command."
            )
            note += para
            return [note]

        node = scenario_appendix_placeholder()
        return [node]


# ---------------------------------------------------------------------------
# Event: replace placeholder with actual appendix content
# ---------------------------------------------------------------------------

def _build_appendix_nodes(
    entries: Dict,
) -> List[nodes.Node]:
    """Build docutils section nodes for every collected appendix entry."""
    # Group by command tag
    by_tag: Dict[str, List] = {}
    for entry in entries.values():
        by_tag.setdefault(entry["command_tag"], []).append(entry)

    # Determine display order
    ordered_tags = sorted(
        by_tag.keys(),
        key=lambda t: (
            _TAG_ORDER.index(t) if t in _TAG_ORDER else len(_TAG_ORDER),
            t,
        ),
    )

    result: List[nodes.Node] = []
    for tag in ordered_tags:
        tag_entries = sorted(by_tag[tag], key=lambda e: e["feature_title"])
        label = f"appendix-{tag}"
        section_title = _TAG_LABELS.get(tag, f"``dfetch {tag}`` scenarios")

        tag_section = nodes.section()
        tag_section["ids"] = [label]
        tag_section["names"] = [label]
        tag_section += nodes.title(text=section_title)

        for entry in tag_entries:
            feat_section = nodes.section()
            feat_section["ids"] = [entry["label"]]
            feat_section["names"] = [entry["label"]]
            feat_section += nodes.title(text=entry["feature_title"])

            content = _full_feature_content(entry["feature_abs"])
            code = nodes.literal_block(content, content)
            code["language"] = "gherkin"
            feat_section += code

            tag_section += feat_section

        result.append(tag_section)

    return result


def process_scenario_appendix(
    app, doctree: nodes.document, fromdocname: str
) -> None:
    """Replace scenario_appendix_placeholder nodes with generated content."""
    placeholders = list(doctree.traverse(scenario_appendix_placeholder))
    if not placeholders:
        return

    entries = getattr(app.env, "scenario_appendix_entries", {})
    appendix_nodes = _build_appendix_nodes(entries) if entries else []

    for placeholder in placeholders:
        placeholder.replace_self(appendix_nodes)


def purge_scenario_appendix(app, env, docname: str) -> None:
    """Remove appendix entries that originated from a re-read document."""
    if not hasattr(env, "scenario_appendix_entries"):
        return
    env.scenario_appendix_entries = {
        k: v
        for k, v in env.scenario_appendix_entries.items()
        if v.get("source_doc") != docname
    }


def merge_scenario_appendix(app, env, docnames, other) -> None:
    """Merge appendix entries from a parallel read worker."""
    if not hasattr(env, "scenario_appendix_entries"):
        env.scenario_appendix_entries = {}
    for key, entry in getattr(other, "scenario_appendix_entries", {}).items():
        if key not in env.scenario_appendix_entries:
            env.scenario_appendix_entries[key] = entry
        else:
            existing = env.scenario_appendix_entries[key]
            for scenario in entry["scenarios"]:
                if scenario not in existing["scenarios"]:
                    existing["scenarios"].append(scenario)


# ---------------------------------------------------------------------------
# Sphinx extension setup
# ---------------------------------------------------------------------------


def setup(app):
    """Register directives, nodes, and event hooks."""
    app.add_directive("scenario-include", ScenarioIncludeDirective)
    app.add_directive("scenario-appendix", ScenarioAppendixDirective)
    app.add_node(scenario_appendix_placeholder)
    app.connect("doctree-resolved", process_scenario_appendix)
    app.connect("env-purge-doc", purge_scenario_appendix)
    app.connect("env-merge-info", merge_scenario_appendix)

    return {
        "version": "0.2",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
