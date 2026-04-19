"""
Custom Sphinx directive for including feature examples from feature files.

Usage in conf.py:

    extensions = ["scenario_directive"]

    # Tags that are NOT group keys (e.g. environment markers).
    # The first tag on a feature file that is not in this list becomes
    # the appendix section for that file.  Default: no exclusions.
    scenario_non_command_tags = ["remote-svn"]

Usage in .rst files:

    .. scenario-include:: ../features/fetch-git-repo.feature
       :scenario:
          Example Title 1
          Example Title 2

If ``:scenario:`` is omitted, all examples in the feature file are included.

**PDF / LaTeX builds** automatically move examples to an appendix grouped by
the first non-excluded behave tag found on the feature file.  The directive's
original location receives a cross-reference to the appendix entry instead.

Use the ``:inline:`` flag to keep a specific inclusion in place even when
building a PDF:

    .. scenario-include:: ../features/fetch-git-repo.feature
       :inline:

The appendix itself is rendered by placing the companion directive anywhere in
the document tree:

    .. scenario-appendix::
"""

import html
import os
import re
from typing import Dict, FrozenSet, List, Tuple

from docutils import nodes
from docutils.parsers.rst import Directive, directives
from docutils.statemachine import StringList
from sphinx.util import logging
from sphinx.util.nodes import make_refnode

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Custom node types
# ---------------------------------------------------------------------------


class ScenarioAppendixPlaceholder(nodes.General, nodes.Element):
    """Replaced by the full appendix content during the resolve phase."""


class ScenarioAppendixRef(nodes.General, nodes.Element):
    """Deferred cross-reference to a scenario appendix entry.

    Stores ``label``, ``reftitle``, ``group_tag``, and ``group_label`` as
    attributes.  Resolved to a paragraph with ``make_refnode`` links during
    ``doctree-resolved``, once the appendix document name is known.
    """


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


def _group_tag(feature_path: str, non_group_tags: FrozenSet[str]) -> str:
    """Return the first tag not in *non_group_tags*, or ``'other'``."""
    for tag in _feature_tags(feature_path):
        if tag not in non_group_tags:
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


def _all_scenarios(feature_path: str) -> Tuple[Tuple[str, str], ...]:
    """Return (header, title) pairs for all scenarios in the feature file."""
    with open(feature_path, encoding="utf-8") as fh:
        return tuple(
            (m[0], m[1])
            for m in re.findall(
                r"^\s*(Scenario(?:\s+Outline)?):\s*(.+)$", fh.read(), re.MULTILINE
            )
        )


def _full_feature_content(feature_path: str) -> str:
    """Return the complete textual content of a feature file."""
    with open(feature_path, encoding="utf-8") as fh:
        return fh.read()


def _selected_scenarios_content(feature_path: str, scenario_titles: List[str]) -> str:
    """Return content containing only the selected scenario blocks."""
    with open(feature_path, encoding="utf-8") as fh:
        content = fh.read()
    blocks = []
    for title in scenario_titles:
        pattern = re.compile(
            r"([ \t]*Scenario(?:[ \t]+Outline)?:[ \t]*"
            + re.escape(title)
            + r"[ \t]*\n(?:(?![ \t]*Scenario(?:[ \t]+Outline)?:).)*)",
            re.DOTALL,
        )
        match = pattern.search(content)
        if match:
            blocks.append(match.group(1).rstrip())
    return "\n\n".join(blocks)


def _tag_section_title(tag: str) -> str:
    """Human-readable section title derived from *tag* alone."""
    return tag.replace("-", " ").title()


# ---------------------------------------------------------------------------
# scenario-include directive
# ---------------------------------------------------------------------------


class ScenarioIncludeDirective(Directive):
    """Include feature examples from a feature file.

    In PDF/LaTeX builds the examples are moved to a dedicated appendix and
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

    def _env(self):
        return self.state.document.settings.env

    def _is_pdf(self) -> bool:
        return self._env().app.builder.name in ("latex", "rinoh")

    def _feature_abs(self, feature_file: str) -> str:
        env = self._env()
        path = os.path.abspath(os.path.join(env.app.srcdir, feature_file))
        if not os.path.exists(path):
            raise self.error(f"Feature file not found: {path}")
        return path

    def _include_path(self, feature_abs: str) -> str:
        """Path for literalinclude, relative to the current RST document."""
        env = self._env()
        current_doc_dir = os.path.dirname(os.path.join(env.app.srcdir, env.docname))
        return os.path.relpath(feature_abs, current_doc_dir)

    @staticmethod
    def _end_before(available: Tuple[Tuple[str, str], ...], title: str) -> str:
        """Return the :end-before: value for *title*, or '' for the last scenario."""
        all_titles = tuple(t for _, t in available)
        try:
            idx = all_titles.index(title)
        except ValueError:
            return ""
        if idx < len(available) - 1:
            next_header, next_title = available[idx + 1]
            return f":end-before: {next_header}: {next_title}"
        return ""

    def _requested_scenarios(self, available: Tuple[Tuple[str, str], ...]) -> List[str]:
        return [
            t.strip()
            for t in self.options.get("scenario", "").splitlines()
            if t.strip()
        ] or [title for _, title in available]

    # ------------------------------------------------------------------
    # HTML / inline rendering (original behaviour)
    # ------------------------------------------------------------------

    def _render_html(
        self,
        include_path: str,
        feature_file: str,
        scenario_titles: List[str],
        available: Tuple[Tuple[str, str], ...],
    ) -> List[nodes.Node]:
        title_to_header = {title: header for header, title in available}
        container = nodes.section()
        for title in scenario_titles:
            header = title_to_header.get(title, "Scenario")
            end_before = self._end_before(available, title)
            directive_rst = f"""
.. raw:: html

   <details>
   <summary><strong>Example</strong>: {html.escape(title)}</summary>

.. literalinclude:: {include_path}
    :language: gherkin
    :caption: {feature_file}
    :force:
    :dedent:
    :start-after: {header}: {title}
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
        env = self._env()
        non_group_tags = frozenset(getattr(env.config, "scenario_non_command_tags", []))
        basename = os.path.splitext(os.path.basename(feature_abs))[0]
        label = f"appendix-{basename}"
        tag = _group_tag(feature_abs, non_group_tags)
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
                "group_tag": tag,
                "label": label,
                "source_docs": {env.docname},
                "scenarios": list(scenario_titles),
            }
        else:
            existing = env.scenario_appendix_entries[feature_abs]
            existing["source_docs"].add(env.docname)
            for s in scenario_titles:
                if s not in existing["scenarios"]:
                    existing["scenarios"].append(s)

        # ----------------------------------------------------------
        # Return a deferred ScenarioAppendixRef block node.  It is
        # resolved to a full paragraph with make_refnode links during
        # doctree-resolved, once the appendix document name is known.
        # Sphinx's make_refnode handles LaTeX/HTML builder differences,
        # producing a proper \hyperref in PDF output.
        # ----------------------------------------------------------
        ref_node = ScenarioAppendixRef()
        ref_node["label"] = label
        ref_node["reftitle"] = title
        ref_node["group_tag"] = tag
        ref_node["group_label"] = f"appendix-{tag}"
        ref_node["scenario_count"] = len(scenario_titles)
        return [ref_node]

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def run(self) -> List[nodes.Node]:
        feature_file = self.arguments[0].strip()
        feature_abs = self._feature_abs(feature_file)
        available = _all_scenarios(feature_abs)
        scenario_titles = self._requested_scenarios(available)

        if "scenario" in self.options:
            available_titles = {title for _, title in available}
            requested = [
                t.strip() for t in self.options["scenario"].splitlines() if t.strip()
            ]
            missing = [t for t in requested if t not in available_titles]
            if missing:
                raise self.error(
                    f"Scenario(s) not found in {feature_file}: {', '.join(missing)}"
                )
            if not scenario_titles:
                raise self.error(f"No scenarios matched in {feature_file}.")

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
    """Render the appendix of all PDF-deferred feature examples.

    Place this directive once in the document (typically in an appendix
    page).  During the write phase it is replaced by sections grouped by
    the first non-excluded tag, sorted alphabetically, containing the full
    content of each referenced feature file.

    In HTML builds examples appear inline in the main text, so this
    directive emits an explanatory note instead.
    """

    required_arguments = 0
    optional_arguments = 0
    has_content = False

    def run(self) -> List[nodes.Node]:
        env = self.state.document.settings.env
        if env.app.builder.name not in ("latex", "rinoh"):
            note = nodes.note()
            para = nodes.paragraph()
            para += nodes.Text(
                "In the HTML edition, feature examples appear as expandable "
                "blocks directly within each guide section. "
                "In the PDF edition they are collected here, grouped by command."
            )
            note += para
            return [note]

        # Record which document hosts the appendix so that ScenarioAppendixRef
        # nodes in other documents can be resolved with the correct refdocname.
        env.scenario_appendix_docname = env.docname
        node = ScenarioAppendixPlaceholder()
        return [node]


# ---------------------------------------------------------------------------
# Event: replace placeholder with actual appendix content
# ---------------------------------------------------------------------------


def _build_appendix_nodes(entries: Dict) -> List[nodes.Node]:
    """Build docutils section nodes for every collected appendix entry."""
    by_tag: Dict[str, List] = {}
    for entry in entries.values():
        by_tag.setdefault(entry["group_tag"], []).append(entry)

    result: List[nodes.Node] = []
    for tag in sorted(by_tag):
        tag_entries = sorted(by_tag[tag], key=lambda e: e["feature_title"])
        label = f"appendix-{tag}"

        tag_section = nodes.section()
        tag_section["ids"] = [label]
        tag_section["names"] = [label]
        tag_section += nodes.title(text=_tag_section_title(tag))

        for entry in tag_entries:
            feat_section = nodes.section()
            feat_section["ids"] = [entry["label"]]
            feat_section["names"] = [entry["label"]]
            feat_section += nodes.title(text=entry["feature_title"])

            content = _selected_scenarios_content(
                entry["feature_abs"], entry["scenarios"]
            )
            code = nodes.literal_block(content, content)
            code["language"] = "gherkin"
            feat_section += code

            tag_section += feat_section

        result.append(tag_section)

    return result


def resolve_scenario_appendix_refs(
    app, doctree: nodes.document, fromdocname: str
) -> None:
    """Replace ScenarioAppendixRef nodes with a paragraph containing clickable links.

    Called for every document during doctree-resolved.  By that point all
    source files have been read so ``env.scenario_appendix_docname`` is set.
    ``make_refnode`` is used so that both the HTML and LaTeX (PDF) builders
    receive a properly formed internal reference — LaTeX needs this to emit a
    working ``\\hyperref``.

    The paragraph text names the group section so readers can locate the entry
    without guessing where in the appendix it lives, e.g.:

        See "Fetch Git Repo" example in the Fetch section of the Appendix.
    """
    appendix_docname = getattr(app.env, "scenario_appendix_docname", None)
    for ref_node in doctree.traverse(ScenarioAppendixRef):
        label = ref_node["label"]
        title = ref_node["reftitle"]
        group_tag = ref_node.get("group_tag", "")
        group_label = ref_node.get("group_label", "")

        count = ref_node.get("scenario_count", 1)
        examples = "examples" if count > 1 else "example"

        para = nodes.paragraph()
        if appendix_docname:
            feat_ref = make_refnode(
                app.builder,
                fromdocname,
                appendix_docname,
                label,
                nodes.inline("", title),
            )
            para += nodes.Text("See \u201c")
            para += feat_ref
            para += nodes.Text(f"\u201d {examples}")
            if group_label and group_tag:
                group_ref = make_refnode(
                    app.builder,
                    fromdocname,
                    appendix_docname,
                    group_label,
                    nodes.inline("", _tag_section_title(group_tag)),
                )
                para += nodes.Text(" in the ")
                para += group_ref
                para += nodes.Text(" section of the Appendix.")
            else:
                para += nodes.Text(" in the Appendix.")
        else:
            logger.warning(
                "PDF build will omit deferred scenario examples because no "
                "'.. scenario-appendix::' directive was found in the document tree; "
                "add it to a page (e.g. an appendix) to include deferred examples.",
                location=ref_node,
            )
            para += nodes.Text(f"See \u201c{title}\u201d {examples} in the Appendix.")

        ref_node.replace_self(para)


def process_scenario_appendix(app, doctree: nodes.document, _fromdocname: str) -> None:
    """Replace ScenarioAppendixPlaceholder nodes with generated content."""
    placeholders = list(doctree.traverse(ScenarioAppendixPlaceholder))
    if not placeholders:
        return

    entries = getattr(app.env, "scenario_appendix_entries", {})
    appendix_nodes = _build_appendix_nodes(entries) if entries else []

    for placeholder in placeholders:
        placeholder.replace_self(appendix_nodes)


def purge_scenario_appendix(_app, env, docname: str) -> None:
    """Remove appendix entries that originated from a re-read document."""
    if not hasattr(env, "scenario_appendix_entries"):
        return
    to_delete = []
    for k, v in env.scenario_appendix_entries.items():
        v["source_docs"].discard(docname)
        if not v["source_docs"]:
            to_delete.append(k)
    for k in to_delete:
        del env.scenario_appendix_entries[k]


def merge_scenario_appendix(_app, env, _docnames, other) -> None:
    """Merge appendix entries from a parallel read worker."""
    if hasattr(other, "scenario_appendix_docname") and not hasattr(
        env, "scenario_appendix_docname"
    ):
        env.scenario_appendix_docname = other.scenario_appendix_docname
    if not hasattr(env, "scenario_appendix_entries"):
        env.scenario_appendix_entries = {}
    for key, entry in getattr(other, "scenario_appendix_entries", {}).items():
        if key not in env.scenario_appendix_entries:
            env.scenario_appendix_entries[key] = entry
        else:
            existing = env.scenario_appendix_entries[key]
            existing["source_docs"].update(entry["source_docs"])
            for scenario in entry["scenarios"]:
                if scenario not in existing["scenarios"]:
                    existing["scenarios"].append(scenario)


# ---------------------------------------------------------------------------
# Sphinx extension setup
# ---------------------------------------------------------------------------


def setup(app):
    """Register directives, nodes, and event hooks."""
    app.add_config_value("scenario_non_command_tags", [], "env")
    app.add_directive("scenario-include", ScenarioIncludeDirective)
    app.add_directive("scenario-appendix", ScenarioAppendixDirective)
    app.add_node(ScenarioAppendixPlaceholder)
    app.add_node(ScenarioAppendixRef)
    app.connect("doctree-resolved", resolve_scenario_appendix_refs)
    app.connect("doctree-resolved", process_scenario_appendix)
    app.connect("env-purge-doc", purge_scenario_appendix)
    app.connect("env-merge-info", merge_scenario_appendix)

    return {
        "version": "0.3",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
