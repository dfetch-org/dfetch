"""Sphinx extension: ``.. pytm::`` directive.

Renders asset, data-flow, control, gap, and STRIDE-threat tables directly
from an executable pytm threat model, with no pre-generated intermediate
files.

Incremental builds
------------------
Each document that contains a ``.. pytm::`` directive registers the model
file as a dependency via ``env.note_dependency()``.  Sphinx therefore
rebuilds the document whenever the model changes without requiring a full
clean build.

Within a single Sphinx invocation the model is loaded once: the
``builder-inited`` event (single-threaded) preloads the configured model
and stores the result in ``app._pytm_cache``.  Subsequent directive
executions — including parallel reads — only read from the cache, so no
locking is required.

Configuration
-------------
``pytm_model`` (str)
    Absolute path to the threat-model Python file.  Set in ``conf.py``::

        import os
        pytm_model = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..', 'security', 'threat_model.py')
        )

Usage in .rst files
-------------------
::

    .. pytm::
       :assets:
       :dataflows:
       :controls:
       :gaps:
       :threats:

All options are independent flags; any subset may be combined.  An explicit
model path overrides the ``pytm_model`` config value::

    .. pytm:: ../security/threat_model.py
       :assets:
"""

from __future__ import annotations

import importlib.util
import os
import sys
import threading
from typing import TYPE_CHECKING, Any

from docutils import nodes
from docutils.parsers.rst import Directive, directives
from docutils.statemachine import StringList
from sphinx.util import logging

if TYPE_CHECKING:
    from sphinx.application import Sphinx

logger = logging.getLogger(__name__)

_load_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Directive
# ---------------------------------------------------------------------------


class PytmDirective(Directive):
    """Render sections of a pytm threat model as RST tables."""

    optional_arguments = 1
    has_content = False
    option_spec = {
        "assets": directives.flag,
        "dataflows": directives.flag,
        "controls": directives.flag,
        "gaps": directives.flag,
        "threats": directives.flag,
    }

    def run(self) -> list[nodes.Node]:
        env = self.state.document.settings.env
        app = env.app

        model_path = self._resolve_path(app)
        if model_path is None:
            return [
                nodes.error(
                    None,
                    nodes.paragraph(
                        text=(
                            "pytm directive: no model path. "
                            "Pass a path argument or set pytm_model in conf.py."
                        )
                    ),
                )
            ]

        if not os.path.isfile(model_path):
            return [
                nodes.error(
                    None,
                    nodes.paragraph(text=f"pytm directive: model not found: {model_path}"),
                )
            ]

        # Mark this document as depending on the model file so Sphinx
        # rebuilds it whenever the model changes.
        env.note_dependency(model_path)

        data = _get_model_data(app, model_path)

        sections: list[str] = []
        if "assets" in self.options:
            sections.append(_render_assets(data["assets"]))
        if "dataflows" in self.options:
            sections.append(_render_dataflows(data["dataflows"]))
        if "controls" in self.options:
            sections.append(_render_controls(data["controls"]))
        if "gaps" in self.options:
            sections.append(_render_gaps(data["gaps"]))
        if "threats" in self.options:
            sections.append(_render_threats(data["threats"]))

        rst = "\n\n".join(sections)
        return _parse_rst(rst, self.state, self.content_offset, model_path)

    def _resolve_path(self, app: Any) -> str | None:
        if self.arguments:
            raw = self.arguments[0]
            if os.path.isabs(raw):
                return raw
            return os.path.normpath(os.path.join(app.confdir, raw))
        return getattr(app.config, "pytm_model", None)


# ---------------------------------------------------------------------------
# Model loading and caching
# ---------------------------------------------------------------------------


def _get_model_data(app: Any, model_path: str) -> dict:
    """Return cached model data, loading on first access (thread-safe)."""
    cache: dict = getattr(app, "_pytm_cache", {})
    mtime = os.path.getmtime(model_path)
    key = (model_path, mtime)
    if key in cache:
        return cache[key]
    with _load_lock:
        # Re-check after acquiring lock (another thread may have loaded it).
        if key not in cache:
            cache[key] = _load_model(model_path, app.confdir)
            app._pytm_cache = cache
    return cache[key]


def _load_model(model_path: str, confdir: str) -> dict:
    """Import the threat model file and extract all structured data."""
    from pytm import TM, Data, Dataflow, Datastore, ExternalEntity  # type: ignore[import]

    # The model calls TM.reset() at module level; executing it again resets
    # the singleton cleanly.
    TM.reset()

    spec = importlib.util.spec_from_file_location("_pytm_model_tmp", model_path)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    # resolve() computes STRIDE findings without touching sys.argv or I/O.
    mod.tm.resolve()

    # -- Assets --------------------------------------------------------------
    # pytm stores Data objects in TM._data, not TM._elements.
    from pytm import Process  # type: ignore[import]

    id_prefixes = ("PA-", "SA-", "EA-", "DA-", "HW-", "FA-", "NI-", "OA-")
    candidate_elements = list(TM._elements) + list(getattr(TM, "_data", []))
    assets: list[dict] = []
    for el in candidate_elements:
        if not isinstance(el, (Datastore, ExternalEntity, Data, Process)):
            continue
        if not any(el.name.startswith(p) for p in id_prefixes):
            continue
        asset_id, sep, asset_name = el.name.partition(":")
        assets.append(
            {
                "id": asset_id.strip(),
                "name": asset_name.strip() if sep else el.name,
                "type": type(el).__name__,
                "classification": _fmt_classification(
                    getattr(el, "classification", None)
                ),
                "description": (getattr(el, "description", "") or "").strip(),
            }
        )
    assets.sort(key=lambda a: _sort_key(a["id"]))

    # -- Dataflows -----------------------------------------------------------
    dataflows: list[dict] = []
    for el in TM._elements:
        if not isinstance(el, Dataflow):
            continue
        if not el.name.startswith("DF-"):
            continue
        flow_id, sep, flow_name = el.name.partition(":")
        dataflows.append(
            {
                "id": flow_id.strip(),
                "flow": flow_name.strip() if sep else el.name,
                "protocol": (getattr(el, "protocol", "") or "").strip(),
                "description": (getattr(el, "description", "") or "").strip(),
            }
        )
    dataflows.sort(key=lambda d: _sort_key(d["id"]))

    # -- STRIDE findings -----------------------------------------------------
    threats: list[dict] = []
    for finding in mod.tm.findings:
        threats.append(
            {
                "id": finding.threat_id,
                "element": finding.element.name,
                "description": finding.description,
                "severity": str(finding.severity),
                "mitigations": (finding.mitigations or "").strip(),
            }
        )

    # -- Module-level CONTROLS and GAPS (optional) ---------------------------
    controls: list[dict] = list(getattr(mod, "CONTROLS", []))
    gaps: list[dict] = list(getattr(mod, "GAPS", []))

    return {
        "assets": assets,
        "dataflows": dataflows,
        "threats": threats,
        "controls": controls,
        "gaps": gaps,
    }


_PREFIX_ORDER = {
    # ISO/IEC 27005 / EN 18031 taxonomy
    "PA": 0, "SA": 1, "EA": 2,
    # EN 40000 five-category taxonomy
    "DA": 0, "HW": 1, "FA": 2, "NI": 3, "OA": 4,
}


def _sort_key(asset_id: str) -> tuple:
    """Sort PA-01 < PA-02 < ... < SA-01 < ... < EA-01 numerically."""
    prefix = asset_id[:2] if len(asset_id) >= 2 else asset_id
    order = _PREFIX_ORDER.get(prefix, 99)
    try:
        num = int(asset_id.split("-", 1)[1])
    except (IndexError, ValueError):
        num = 0
    return (order, prefix, num)


def _fmt_classification(cls: Any) -> str:
    if cls is None:
        return ""
    name = getattr(cls, "name", str(cls))
    return name.replace("_", " ").title()


# ---------------------------------------------------------------------------
# RST table builders
# ---------------------------------------------------------------------------


def _cell(text: str) -> str:
    """Flatten and RST-escape text for a single list-table cell line."""
    text = text.replace("\n", " ").strip()
    if not text:
        return "—"
    # Escape lone asterisks (glob patterns like *.yml confuse RST emphasis parser).
    # We only escape * that are NOT already doubled (**bold**).
    import re as _re

    text = _re.sub(r"(?<!\*)\*(?!\*)", r"\\*", text)
    return text


def _list_table(headers: list[str], rows: list[list[str]], widths: list[int]) -> str:
    """Build a ``.. list-table::`` RST block."""
    lines = [
        ".. list-table::",
        "   :header-rows: 1",
        f'   :widths: {" ".join(str(w) for w in widths)}',
        "",
        "   * - " + headers[0],
    ]
    for h in headers[1:]:
        lines.append("     - " + h)
    for row in rows:
        lines.append("   * - " + row[0])
        for cell in row[1:]:
            lines.append("     - " + cell)
    return "\n".join(lines)


def _render_assets(assets: list[dict]) -> str:
    if not assets:
        return ".. note::\n\n   No assets with standard ID prefixes found in model."
    headers = ["ID", "Name", "Classification", "Description"]
    widths = [8, 28, 14, 50]
    rows = [
        [a["id"], a["name"], a["classification"], _cell(a["description"])]
        for a in assets
    ]
    return _list_table(headers, rows, widths)


def _render_dataflows(dataflows: list[dict]) -> str:
    if not dataflows:
        return ".. note::\n\n   No data flows with DF- prefix found in model."
    headers = ["ID", "Flow", "Protocol", "Notes"]
    widths = [8, 30, 14, 48]
    rows = [
        [
            d["id"],
            d["flow"],
            d["protocol"] or "(local)",
            _cell(d["description"]),
        ]
        for d in dataflows
    ]
    return _list_table(headers, rows, widths)


def _render_controls(controls: list[dict]) -> str:
    if not controls:
        return (
            ".. note::\n\n   No controls defined.  "
            "Add a ``CONTROLS`` list to the threat model."
        )
    headers = ["Control", "Asset(s) protected", "Implementation"]
    widths = [28, 18, 54]
    rows = []
    for c in controls:
        impl = _cell(c.get("implementation", ""))
        ref = c.get("reference", "")
        if ref:
            impl += f"  ``{ref}``"
        rows.append(
            [
                c.get("name", "—"),
                ", ".join(c.get("assets", [])),
                impl,
            ]
        )
    return _list_table(headers, rows, widths)


def _render_gaps(gaps: list[dict]) -> str:
    if not gaps:
        return (
            ".. note::\n\n   No gaps defined.  "
            "Add a ``GAPS`` list to the threat model."
        )
    headers = ["Gap", "Description"]
    widths = [30, 70]
    rows = [
        [g.get("name", "—"), _cell(g.get("description", ""))]
        for g in gaps
    ]
    return _list_table(headers, rows, widths)


def _render_threats(threats: list[dict]) -> str:
    if not threats:
        return (
            ".. note::\n\n   No STRIDE findings "
            "(all threats mitigated or no elements in scope)."
        )
    # Group by severity for readability: Very High > High > Medium > Low
    sev_order = {"Very High": 0, "High": 1, "Medium": 2, "Low": 3}
    sorted_threats = sorted(
        threats, key=lambda t: (sev_order.get(t["severity"], 9), t["id"])
    )
    headers = ["Threat ID", "Severity", "Element", "Description"]
    widths = [10, 10, 25, 55]
    rows = [
        [
            t["id"],
            t["severity"],
            t["element"],
            _cell(t["description"]),
        ]
        for t in sorted_threats
    ]
    return _list_table(headers, rows, widths)


# ---------------------------------------------------------------------------
# RST → docutils nodes
# ---------------------------------------------------------------------------


def _parse_rst(
    rst: str, state: Any, content_offset: int, source_label: str
) -> list[nodes.Node]:
    container = nodes.section()
    container.document = state.document
    view = StringList()
    basename = os.path.basename(source_label)
    for i, line in enumerate(rst.splitlines()):
        view.append(line, f"<pytm: {basename}>", i)
    state.nested_parse(view, content_offset, container)
    return container.children  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Builder-inited hook: preload the default model (single-threaded)
# ---------------------------------------------------------------------------


def _on_builder_inited(app: Sphinx) -> None:
    """Preload the configured model so directive runs only read from cache."""
    model_path: str | None = getattr(app.config, "pytm_model", None)
    if not model_path or not os.path.isfile(model_path):
        return
    try:
        mtime = os.path.getmtime(model_path)
        data = _load_model(model_path, app.confdir)
        app._pytm_cache = {(model_path, mtime): data}
        logger.info(
            f"pytm: loaded {len(data['assets'])} assets, "
            f"{len(data['dataflows'])} flows, "
            f"{len(data['threats'])} STRIDE findings "
            f"from {os.path.basename(model_path)}"
        )
    except Exception as exc:
        logger.warning(f"pytm: failed to preload model: {exc}", exc_info=True)


# ---------------------------------------------------------------------------
# Extension entry point
# ---------------------------------------------------------------------------


def setup(app: Sphinx) -> dict:
    app.add_config_value("pytm_model", default=None, rebuild="env")
    app.add_directive("pytm", PytmDirective)
    app.connect("builder-inited", _on_builder_inited)
    return {
        "version": "1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
