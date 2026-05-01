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

import contextlib
import dataclasses as _dc
import importlib.util
import io as _io
import os
import re as _re
import threading
from typing import TYPE_CHECKING, Any

from docutils import nodes
from docutils.parsers.rst import Directive, directives
from docutils.statemachine import StringList
from pytm import (
    TM,
)
from pytm import Actor as _Actor
from pytm import (
    Data,
    Dataflow,
    Datastore,
    ExternalEntity,
    Process,
)
from sphinx.util import logging

if TYPE_CHECKING:
    from sphinx.application import Sphinx

logger = logging.getLogger(__name__)

_load_lock = threading.Lock()
_model_cache: dict[tuple[str, float], dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# Directive
# ---------------------------------------------------------------------------


class PytmDirective(Directive):
    """Render sections of a pytm threat model as RST tables."""

    optional_arguments = 1
    has_content = False
    option_spec = {
        "assumptions": directives.flag,
        "boundaries": directives.flag,
        "actors": directives.flag,
        "assets": directives.flag,
        "dataflows": directives.flag,
        "controls": directives.flag,
        "gaps": directives.flag,
        "threats": directives.flag,
        "seq": directives.flag,
        "dfd": directives.flag,
    }

    def run(self) -> list[nodes.Node]:
        env = self.state.document.settings.env
        app = env.app

        model_path = self._resolve_path(app)
        if model_path is None:
            return [
                nodes.error(
                    "No model path",
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
                    "Model not found",
                    nodes.paragraph(
                        text=f"pytm directive: model not found: {model_path}"
                    ),
                )
            ]

        # Mark this document as depending on the model file so Sphinx
        # rebuilds it whenever the model changes.
        env.note_dependency(model_path)

        data = _get_model_data(model_path)

        sections: list[str] = []
        if "assumptions" in self.options:
            sections.append(_render_assumptions(data["assumptions"]))
        if "boundaries" in self.options:
            sections.append(_render_boundaries(data["boundaries"]))
        if "actors" in self.options:
            sections.append(_render_actors(data["actors"]))
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
        if "seq" in self.options:
            sections.append(
                _render_seq(data.get("seq", ""), data.get("seq_img_path", ""))
            )
        if "dfd" in self.options:
            sections.append(
                _render_dfd(data.get("dfd", ""), data.get("dfd_img_path", ""))
            )

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


def _get_model_data(model_path: str) -> dict:
    """Return cached model data, loading on first access (thread-safe)."""
    mtime = os.path.getmtime(model_path)
    key = (model_path, mtime)
    if key in _model_cache:
        return _model_cache[key]
    with _load_lock:
        # Re-check after acquiring lock (another thread may have loaded it).
        if key not in _model_cache:
            _model_cache[key] = _load_model(model_path)
    return _model_cache[key]


_ID_PREFIXES = ("PA-", "SA-", "EA-", "DA-", "HW-", "FA-", "NI-", "OA-")


def _extract_assets(candidate_elements: list) -> list[dict]:
    assets: list[dict] = []
    for el in candidate_elements:
        if not isinstance(el, (Datastore, ExternalEntity, Data, Process)):
            continue
        if not any(el.name.startswith(p) for p in _ID_PREFIXES):
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
    return assets


def _extract_dataflows(elements: list) -> list[dict]:
    dataflows: list[dict] = []
    for el in elements:
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
    return dataflows


def _extract_raw_threats() -> list[dict]:
    threats: list[dict] = []
    for thr in getattr(TM, "_threats", []):
        threats.append(
            {
                "id": getattr(thr, "id", ""),
                "description": getattr(thr, "description", "") or "",
                "details": getattr(thr, "details", "") or "",
                "likelihood": str(getattr(thr, "likelihood", "") or ""),
                "severity": str(getattr(thr, "severity", "") or ""),
                "mitigations": getattr(thr, "mitigations", "") or "",
                "prerequisites": getattr(thr, "prerequisites", "") or "",
                "example": getattr(thr, "example", "") or "",
                "references": getattr(thr, "references", "") or "",
                "controls": [],
            }
        )
    sev_order = {"Very High": 0, "High": 1, "Medium": 2, "Low": 3}
    threats.sort(key=lambda t: (sev_order.get(t["severity"], 9), t["id"]))
    return threats


def _extract_controls_and_gaps(mod: Any) -> tuple[list[dict], list[dict]]:
    all_controls = list(getattr(mod, "CONTROLS", []))
    if all_controls and _dc.is_dataclass(all_controls[0]):
        controls = [_dc.asdict(c) for c in all_controls if c.status == "implemented"]
        gaps = [_dc.asdict(c) for c in all_controls if c.status != "implemented"]
    else:
        controls = [
            c for c in all_controls if c.get("status", "implemented") == "implemented"
        ]
        gaps = list(getattr(mod, "GAPS", []))
    return controls, gaps


def _apply_threat_controls(
    threats: list[dict], controls: list[dict], gaps: list[dict]
) -> None:
    threat_controls_map: dict[str, list[str]] = {}
    for ctrl in controls + gaps:
        for sid in ctrl.get("threats", []):
            threat_controls_map.setdefault(sid, []).append(ctrl["id"])
    for thr in threats:
        thr["controls"] = threat_controls_map.get(thr["id"], [])


def _generate_diagrams(mod: Any, confdir: str = "") -> tuple[str, str, str, str]:
    seq_str = ""
    dfd_str = ""
    buf = _io.StringIO()
    with contextlib.suppress(Exception), contextlib.redirect_stdout(buf):
        result = mod.tm.seq()
        seq_str = (
            result if isinstance(result, str) and result.strip() else buf.getvalue()
        )
    buf = _io.StringIO()
    with contextlib.suppress(Exception), contextlib.redirect_stdout(buf):
        result = mod.tm.dfd()
        dfd_str = (
            result if isinstance(result, str) and result.strip() else buf.getvalue()
        )

    seq_img_path = ""
    dfd_img_path = ""
    if confdir:
        with contextlib.suppress(Exception):
            from plantweb.render import render as _pw_render

            pytm_static = os.path.join(confdir, "_static", "pytm")
            os.makedirs(pytm_static, exist_ok=True)
            if seq_str:
                out = os.path.join(pytm_static, "threat_model_seq.png")
                _fmt, data = _pw_render(
                    seq_str.encode(), engine="plantuml", format="png"
                )
                with open(out, "wb") as fh:
                    fh.write(data)
                seq_img_path = "/_static/pytm/threat_model_seq.png"
            if dfd_str:
                dfd_puml = f"@startdot\n{dfd_str.strip()}\n@enddot"
                out = os.path.join(pytm_static, "threat_model_dfd.png")
                _fmt, data = _pw_render(
                    dfd_puml.encode(), engine="plantuml", format="png"
                )
                with open(out, "wb") as fh:
                    fh.write(data)
                dfd_img_path = "/_static/pytm/threat_model_dfd.png"

    return seq_str, dfd_str, seq_img_path, dfd_img_path


def _extract_actors(elements: list) -> list[dict]:
    return [
        {
            "name": el.name,
            "boundary": getattr(el.inBoundary, "name", ""),
            "description": (getattr(el, "description", "") or "").strip(),
        }
        for el in elements
        if isinstance(el, _Actor)
    ]


def _extract_boundaries() -> list[dict]:
    return [
        {
            "name": b.name,
            "description": (getattr(b, "description", "") or "").strip(),
        }
        for b in getattr(TM, "_boundaries", [])
    ]


def _extract_assumptions(mod: Any) -> list[dict]:
    return [
        {
            "name": getattr(a, "name", str(a)),
            "description": (getattr(a, "description", "") or "").strip(),
        }
        for a in getattr(mod.tm, "assumptions", [])
    ]


def _load_model(model_path: str, confdir: str = "") -> dict:
    """Import the threat model file and extract all structured data."""
    TM.reset()

    spec = importlib.util.spec_from_file_location("_pytm_model_tmp", model_path)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    mod.tm.resolve()

    elements = list(getattr(TM, "_elements", []))
    candidate_elements = elements + list(getattr(TM, "_data", []))
    threats = _extract_raw_threats()
    controls, gaps = _extract_controls_and_gaps(mod)
    _apply_threat_controls(threats, controls, gaps)
    seq_str, dfd_str, seq_img_path, dfd_img_path = _generate_diagrams(mod, confdir)

    return {
        "assumptions": _extract_assumptions(mod),
        "boundaries": _extract_boundaries(),
        "actors": _extract_actors(elements),
        "assets": _extract_assets(candidate_elements),
        "dataflows": _extract_dataflows(elements),
        "threats": threats,
        "controls": controls,
        "gaps": gaps,
        "seq": seq_str,
        "seq_img_path": seq_img_path,
        "dfd": dfd_str,
        "dfd_img_path": dfd_img_path,
    }


_PREFIX_ORDER = {
    # ISO/IEC 27005 / EN 18031 taxonomy
    "PA": 0,
    "SA": 1,
    "EA": 2,
    # EN 40000 five-category taxonomy
    "DA": 0,
    "HW": 1,
    "FA": 2,
    "NI": 3,
    "OA": 4,
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

    text = _re.sub(r"(?<!\*)\*(?!\*)", r"\\*", text)
    return text


def _ref_list(ids: list[str]) -> str:
    """Return comma-separated :ref: links to the given IDs, or em-dash if empty."""
    filtered = [i for i in ids if i]
    if not filtered:
        return "—"
    return ", ".join(f":ref:`{i} <{i.lower()}>`" for i in filtered)


def _list_table(
    headers: list[str],
    rows: list[list[str]],
    widths: list[int],
    anchor_first_col: bool = False,
) -> str:
    """Build a ``.. list-table::`` RST block with longtable support for LaTeX."""
    total = sum(widths) or 1
    scale = 0.92
    col_spec = "".join(
        f"p{{{w / total * scale:.2f}\\linewidth}}" for w in widths
    )
    lines = [
        f".. tabularcolumns:: {col_spec}",
        "",
        ".. list-table::",
        "   :header-rows: 1",
        f'   :widths: {" ".join(str(w) for w in widths)}',
        "",
        "   * - " + headers[0],
    ]
    for h in headers[1:]:
        lines.append("     - " + h)
    for row in rows:
        if anchor_first_col:
            label = row[0].lower().replace(" ", "-")
            lines.append(f"   * - .. _{label}:")
            lines.append("")
            lines.append(f"       {row[0]}")
        else:
            lines.append("   * - " + row[0])
        for cell in row[1:]:
            lines.append("     - " + cell)
    return "\n".join(lines)


def _render_assumptions(assumptions: list[dict]) -> str:
    if not assumptions:
        return (
            ".. note::\n\n   No assumptions defined.  "
            "Add an ``assumptions`` list to the threat model."
        )
    headers = ["Assumption", "Description"]
    widths = [28, 72]
    rows = [[a["name"], _cell(a["description"])] for a in assumptions]
    return _list_table(headers, rows, widths)


def _render_boundaries(boundaries: list[dict]) -> str:
    if not boundaries:
        return ".. note::\n\n   No trust boundaries defined in model."
    headers = ["Boundary", "Description"]
    widths = [30, 70]
    rows = [[f"**{b['name']}**", _cell(b["description"])] for b in boundaries]
    return _list_table(headers, rows, widths)


def _render_actors(actors: list[dict]) -> str:
    if not actors:
        return ".. note::\n\n   No actors defined in model."
    headers = ["Actor", "Trust Boundary", "Description"]
    widths = [22, 28, 50]
    rows = [
        [f"**{a['name']}**", a["boundary"], _cell(a["description"])] for a in actors
    ]
    return _list_table(headers, rows, widths)


def _render_assets(assets: list[dict]) -> str:
    if not assets:
        return ".. note::\n\n   No assets with standard ID prefixes found in model."
    headers = ["ID", "Name", "Classification", "Description"]
    widths = [8, 28, 14, 50]
    rows = [
        [a["id"], a["name"], a["classification"], _cell(a["description"])]
        for a in assets
    ]
    return _list_table(headers, rows, widths, anchor_first_col=True)


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
    return _list_table(headers, rows, widths, anchor_first_col=True)


def _render_controls(controls: list[dict]) -> str:
    if not controls:
        return (
            ".. note::\n\n   No controls defined.  "
            "Add ``Control`` objects with ``status='implemented'`` "
            "to the ``CONTROLS`` list in the threat model."
        )
    headers = ["ID", "Control", "Asset(s)", "Threat(s)", "Description"]
    widths = [6, 20, 12, 12, 50]
    rows = []
    for c in controls:
        desc = _cell(c.get("description", ""))
        ref = c.get("reference", "")
        if ref:
            desc += f"  ``{ref}``"
        rows.append(
            [
                c.get("id", "—"),
                c.get("name", "—"),
                _ref_list(c.get("assets", [])),
                _ref_list(c.get("threats", [])),
                desc,
            ]
        )
    return _list_table(headers, rows, widths, anchor_first_col=True)


def _render_gaps(gaps: list[dict]) -> str:
    if not gaps:
        return (
            ".. note::\n\n   No gaps defined.  "
            "Add ``Control`` objects with ``status='gap'`` "
            "to the ``CONTROLS`` list in the threat model."
        )
    headers = ["ID", "Gap", "Asset(s)", "Threat(s)", "Description"]
    widths = [6, 22, 12, 12, 48]
    rows = [
        [
            g.get("id", "—"),
            g.get("name", "—"),
            _ref_list(g.get("assets", [])),
            _ref_list(g.get("threats", [])),
            _cell(g.get("description", "")),
        ]
        for g in gaps
    ]
    return _list_table(headers, rows, widths, anchor_first_col=True)


def _render_threats(threats: list[dict]) -> str:
    if not threats:
        return ".. note::\n\n   No threats defined in model."
    # Already sorted by severity then ID in _load_model
    headers = ["ID", "Severity", "Likelihood", "Description", "Controls"]
    widths = [8, 10, 10, 42, 30]
    rows = [
        [
            t["id"],
            t["severity"],
            t["likelihood"],
            _cell(t["description"]),
            _ref_list(t.get("controls", [])),
        ]
        for t in threats
    ]
    return _list_table(headers, rows, widths, anchor_first_col=True)


def _render_seq(seq_str: str, seq_img_path: str = "") -> str:
    if not seq_str or not seq_str.strip():
        return ".. note::\n\n   No sequence diagram generated by the threat model."
    # HTML: plantweb.directive renders via plantuml.com at build time.
    lines = [".. only:: html", "", "   .. uml::", ""]
    for line in seq_str.splitlines():
        lines.append("      " + line if line.strip() else "")
    # LaTeX: use a pre-rendered PNG saved to the source tree so Sphinx
    # copies it to the LaTeX outdir where pdflatex can find it.
    # plantweb saves images to builder.outdir which is NOT the source tree,
    # so ``.. uml::`` inside nested_parse produces a PNG that Sphinx cannot
    # copy correctly for the LaTeX builder.
    if seq_img_path:
        lines += [
            "",
            ".. only:: latex",
            "",
            f"   .. image:: {seq_img_path}",
            "      :align: center",
            "      :width: 100%",
        ]
    return "\n".join(lines)


def _render_dfd(dfd_str: str, dfd_img_path: str = "") -> str:
    if not dfd_str or not dfd_str.strip():
        return ".. note::\n\n   No data-flow diagram generated by the threat model."
    dfd_puml = f"@startdot\n{dfd_str.strip()}\n@enddot"
    lines = [".. only:: html", "", "   .. uml::", ""]
    for line in dfd_puml.splitlines():
        lines.append("      " + line if line.strip() else "")
    if dfd_img_path:
        lines += [
            "",
            ".. only:: latex",
            "",
            f"   .. image:: {dfd_img_path}",
            "      :align: center",
            "      :width: 100%",
        ]
    return "\n".join(lines)


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
        data = _load_model(model_path, confdir=app.confdir)
        _model_cache[(model_path, mtime)] = data
        logger.info(
            f"pytm: loaded {len(data['assumptions'])} assumptions, "
            f"{len(data['boundaries'])} boundaries, "
            f"{len(data['actors'])} actors, "
            f"{len(data['assets'])} assets, "
            f"{len(data['dataflows'])} flows, "
            f"{len(data['threats'])} threats, "
            f"{len(data['controls'])} controls, "
            f"{len(data['gaps'])} gaps "
            f"from {os.path.basename(model_path)}"
        )
    except (
        AttributeError,
        ImportError,
        RuntimeError,
        OSError,
        TypeError,
        ValueError,
        NameError,
        SyntaxError,
        KeyError,
        IndexError,
    ) as exc:
        logger.warning(f"pytm: failed to preload model: {exc}", exc_info=True)


# ---------------------------------------------------------------------------
# Extension entry point
# ---------------------------------------------------------------------------


def setup(app: Sphinx) -> dict:
    """Sphinx extension entry point."""
    app.add_config_value("pytm_model", default=None, rebuild="env")
    app.add_directive("pytm", PytmDirective)
    app.connect("builder-inited", _on_builder_inited)
    return {
        "version": "1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
