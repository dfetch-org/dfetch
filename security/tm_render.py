"""Report and diagram rendering for the dfetch threat models.

Converts pytm findings, controls, and responses into RST table rows,
DFD/sequence diagram content, and orchestrates the full report pipeline.
"""

import os
import re
import sys
from collections.abc import Callable
from typing import Any

from pytm import TM, Data, Element
from pytm.report_util import ReportUtils

from security.tm_elements import Control, ThreatResponse

_RISK_ORDER: dict[str, int] = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}

_DOT: dict[str, str] = {"VH": "🔴", "C": "🔴", "H": "🟠", "M": "🟡", "L": "🟢"}
_SEV_ABBR: dict[str, str] = {"Very High": "VH", "High": "H", "Medium": "M", "Low": "L"}
_RISK_ABBR: dict[str, str] = {"Critical": "C", "High": "H", "Medium": "M", "Low": "L"}
_STRIDE_ABBR: dict[str, str] = {
    "Spoofing": "S",
    "Tampering": "T",
    "Repudiation": "R",
    "Information Disclosure": "I",
    "Denial of Service": "D",
    "Elevation of Privilege": "E",
}


def _abbr_dot(value: str, abbr_map: dict[str, str]) -> str:
    """Abbreviate *value* via *abbr_map* and prefix the matching dot emoji."""
    short = abbr_map.get(value, value)
    return f"{_DOT.get(short, '')}{short}"


_STRIDE_CIA: dict[str, tuple[str, ...]] = {
    "Spoofing": ("C", "I"),
    "Tampering": ("I",),
    "Repudiation": ("I",),
    "Information Disclosure": ("C",),
    "Denial of Service": ("A",),
    "Elevation of Privilege": ("C", "I", "A"),
}


def _update_cia_entry(entry: dict[str, str], resp: ThreatResponse) -> None:
    for stride_cat in resp.stride:
        for dim in _STRIDE_CIA.get(stride_cat, ()):
            cur = entry.get(dim)
            if cur is None or _RISK_ORDER.get(resp.risk, 0) > _RISK_ORDER.get(cur, 0):
                entry[dim] = resp.risk


def _build_cia_map(
    findings: Any,
    controls: list[Control],
    resp_map: dict[str, ThreatResponse],
    assets: list[Any],
) -> dict[str, dict[str, str]]:
    """Build asset-name → CIA rating dict from pytm findings and controls."""
    cia: dict[str, dict[str, str]] = {}
    for f in findings:
        resp = resp_map.get(getattr(f, "threat_id", ""))
        if resp and resp.stride:
            _update_cia_entry(cia.setdefault(str(getattr(f, "target", "")), {}), resp)
    prefix_to_name = {
        getattr(a, "name", "").split(":", maxsplit=1)[0].strip(): getattr(a, "name", "")
        for a in assets
    }
    for ctrl in controls:
        for asset_id in ctrl.assets:
            name = prefix_to_name.get(asset_id)
            if not name:
                continue
            entry = cia.setdefault(name, {})
            for threat_id in ctrl.threats:
                resp = resp_map.get(threat_id)
                if resp and resp.stride:
                    _update_cia_entry(entry, resp)
    return cia


def _asset_row(e: Any, cia: dict[str, dict[str, str]]) -> str:
    name = getattr(e, "name", str(e))
    desc = (getattr(e, "description", "") or "").replace("\n", " ").strip()
    etype = "Data" if isinstance(e, Data) else ReportUtils.getElementType(e)
    rating = cia.get(name, {})
    cia_score = " / ".join(rating.get(dim, "—") for dim in ("C", "I", "A"))
    return (
        f"   * - {name}\n"
        f"     - {desc}\n"
        f"     - {etype}\n"
        f"     - {cia_score}\n"
    )


def _render_asset_rows(
    tm: Any, controls: list[Control], responses: list[ThreatResponse]
) -> str:
    """Return RST list-table rows for all assets, sorted by name.

    CIA dimensions are populated from two sources:
    1. pytm findings: each finding's ThreatResponse STRIDE categories map to C/I/A.
    2. Controls: each control's asset list (short IDs like "A-01") links to threats
       whose STRIDE categories contribute CIA evidence for assets that pytm's threat
       matching may not have surfaced as direct findings.
    The highest risk across all matching findings/controls is used per dimension.
    """
    assets = sorted(
        list(getattr(TM, "_assets")) + list(getattr(TM, "_data", [])),
        key=lambda e: getattr(e, "name", ""),
    )
    if not assets:
        return ""
    resp_map = {r.threat_id: r for r in responses}
    cia = _build_cia_map(tm.findings, controls, resp_map, assets)
    return "".join(_asset_row(e, cia) for e in assets)


def _render_threat_rows(
    tm: Any, controls: list[Control], responses: list[ThreatResponse]
) -> str:
    """Return RST list-table rows, one curated row per threat, sorted by ID.

    pytm emits a finding for every element a threat's condition matches, so a
    threat that applies to many elements produces many byte-identical rows.
    Collapse them to a single row documented against the threat's canonical
    target (``ThreatResponse.target`` when set, otherwise the matched element).
    """
    findings = tm.findings
    if not findings:
        return ""

    resp_map: dict[str, ThreatResponse] = {r.threat_id: r for r in responses}

    representative: dict[str, Any] = {}
    for f in findings:
        representative.setdefault(f.threat_id, f)

    def _row(f: Any) -> str:
        resp = resp_map.get(f.threat_id)
        status = resp.status.capitalize() if resp else "—"
        sev = _abbr_dot(str(f.severity), _SEV_ABBR)
        risk = _abbr_dot(resp.risk, _RISK_ABBR) if resp else "—"
        stride = (
            " ".join(_STRIDE_ABBR.get(s, s) for s in resp.stride)
            if resp and resp.stride
            else "—"
        )
        if resp and resp.status == "mitigate":
            applicable = [ctrl.id for ctrl in controls if f.threat_id in ctrl.threats]
            if not applicable:
                raise ValueError(
                    f"{f.threat_id} has status 'mitigate' but no control references it"
                )
            ctrl_ids = ", ".join(applicable)
            detail = resp.note if resp.note else ctrl_ids
        else:
            detail = resp.note if resp and resp.note else "—"
        target = resp.target if resp and resp.target else str(f.target)
        return (
            f"   * - {f.threat_id}\n"
            f"     - {f.description}\n"
            f"     - {target}\n"
            f"     - | **Sev:** {sev}\n"
            f"       | **Risk:** {risk}\n"
            f"       | **STRIDE:** {stride}\n"
            f"       | **Status:** {status}\n"
            f"     - {detail}\n"
        )

    return "".join(_row(representative[tid]) for tid in sorted(representative))


def _render_control_rows(controls: list[Control]) -> str:
    """Return RST list-table rows for all implemented controls."""
    if not controls:
        return ""

    def _row(c: Control) -> str:
        threats = ", ".join(c.threats) if c.threats else "—"
        desc = c.description
        if c.reference:
            desc += f"  ``{c.reference}``"
        return (
            f"   * - {c.id}\n"
            f"     - {c.name}\n"
            f"     - {threats}\n"
            f"     - {desc}\n"
        )

    return "".join(_row(c) for c in controls)


def _render_finding(f: Any) -> str:
    """Render one pytm Finding as an RST definition list entry."""

    def _val(attr: str) -> str:
        return str(getattr(f, attr, "")).strip()

    threat_id = _val("threat_id")
    description = _val("description")
    lines = [f"{threat_id} — {description}"]
    for label, attr in (
        ("Targeted Element", "target"),
        ("Severity", "severity"),
        ("Example", "example"),
        ("Mitigations", "mitigations"),
        ("References", "references"),
    ):
        value = _val(attr)
        if value:
            lines.append(f"   **{label}:** {value}")
    lines.append("")
    return "\n".join(lines)


def apply_report_utils_patch() -> None:
    """Fix pytm's getInScopeFindings, which always renders empty finding details.

    Two bugs interact:
    1. Finding.target is a str (element name), so getattr(str, 'inScope', False)
       is always False - the default implementation returns [] for every element.
    2. Python's string.Formatter pre-expands {item:call:X} tokens that appear
       inside format specs before the outer format_field sees the spec.  The
       template uses getInScopeFindings as an outer call with getThreatId etc.
       in its sub-template; those inner tokens are evaluated on the *element*
       (not each finding) during Python's spec-expansion step, producing empty
       strings that get baked into the spec before getInScopeFindings can loop.

    Fix: replace getInScopeFindings with one that renders each in-scope finding
    to an RST string directly, so no sub-template is needed in the report.
    element.findings is already scoped to that element, so no target lookup
    is required - the in-scope check on the element itself is sufficient.
    """

    def _fixed(element: Any) -> str:
        if isinstance(element, Data):
            findings = [
                f
                for flow in getattr(element, "carriedBy", [])
                for f in getattr(getattr(flow, "sink", None), "findings", [])
            ]
        elif isinstance(element, Element) and element.inScope:
            findings = element.findings
        else:
            return ""
        if not findings:
            return ""
        return "\n**Threats**\n\n" + "".join(_render_finding(f) for f in findings)

    ReportUtils.getInScopeFindings = staticmethod(_fixed)


def _fix_pytm_dot_output(dot: str) -> str:
    """Replace non-portable pytm image references with Graphviz-native shapes.

    pytm emits absolute filesystem paths like
    ``image = "/home/user/.../pytm/images/datastore_black.png"``
    which break on any machine other than the one that generated the diagram.
    Replace the four-attribute image block with a single portable cylinder shape,
    then rename ``xlabel`` to ``label`` and drop the now-redundant ``label = ""``.
    """
    dot = re.sub(
        r"([ \t]*)shape = none;\n[ \t]*fixedsize = shape;\n"
        r'[ \t]*image = "[^"]*pytm[\\/]+images[\\/][^"]*";\n[ \t]*imagescale = true;',
        r"\1shape = cylinder;",
        dot,
    )
    dot = re.sub(r"\bxlabel\b", "label", dot)
    dot = re.sub(r'[ \t]+label = "";\n', "", dot)
    return dot


# The fullscreen wrapper stays in Python: it uses {uml_block} as a .format()
# target and {{ }}-escaped braces for CSS/JS, which conflict with the RST
# template engine if placed in report_template.rst.
_FULLSCREEN_HTML = """\
.. raw:: html

   <div class="tm-diagram" role="button" tabindex="0" title="Click to view fullscreen">

{uml_block}

.. raw:: html

   </div>
   <style>
   .tm-diagram{{cursor:zoom-in;}}
   .tm-diagram:fullscreen,
   .tm-diagram:-webkit-full-screen{{
     background:#fff;display:flex;
     align-items:center;justify-content:center;
   }}
   .tm-diagram:fullscreen img,
   .tm-diagram:-webkit-full-screen img{{
     max-width:100vw;max-height:100vh;
     width:auto;height:auto;cursor:zoom-out;
   }}
   </style>
   <script>
   (function(){{
     function toggleFs(el){{
       if(!document.fullscreenElement){{
         (el.requestFullscreen||el.webkitRequestFullscreen).call(el);
       }}else{{
         (document.exitFullscreen||document.webkitExitFullscreen).call(document);
       }}
     }}
     document.querySelectorAll('.tm-diagram:not([data-fs])').forEach(function(d){{
       d.dataset.fs='1';
       d.addEventListener('click',function(){{toggleFs(d);}});
       d.addEventListener('keydown',function(e){{
         if(e.key==='Enter'||e.key===' '){{e.preventDefault();toggleFs(d);}}
       }});
     }});
   }})();
   </script>
"""


def _uml_diagram(content: str) -> str:
    """Indent *content*, wrap it in a ``.. uml::`` block, and add fullscreen HTML."""
    indented = "\n".join("   " + line if line else "" for line in content.splitlines())
    return _FULLSCREEN_HTML.format(uml_block=".. uml::\n\n" + indented)


def _render_dfd_section(tm: Any) -> str:
    """Return the DFD as a fullscreen-wrapped ``.. uml::`` block.

    Returns an empty string when ``tm.dfd()`` produces no content.
    The section heading lives in ``report_template.rst``.
    """
    dfd = tm.dfd()
    if not dfd or not dfd.strip():
        return ""
    dfd = _fix_pytm_dot_output(dfd)
    return _uml_diagram("@startdot\n" + dfd + "\n@enddot")


def _wrap_seq_participant_labels(seq: str, max_chars: int = 12) -> str:
    """Wrap long participant labels at word boundaries to narrow each column.

    PlantUML uses a literal ``\\n`` inside quoted strings as a line break.
    Narrower participant boxes shrink the natural diagram width, so when Sphinx
    scales the image to page width the font displays proportionally larger.
    """

    def _wrap(label: str) -> str:
        words = label.split()
        lines: list[str] = []
        current: list[str] = []
        width = 0
        for word in words:
            gap = 1 if current else 0
            if width + gap + len(word) > max_chars and current:
                lines.append(" ".join(current))
                current = [word]
                width = len(word)
            else:
                current.append(word)
                width += gap + len(word)
        if current:
            lines.append(" ".join(current))
        return r"\n".join(lines)

    return re.sub(r'as "([^"]+)"', lambda m: f'as "{_wrap(m.group(1))}"', seq)


def _render_seq_section(tm: Any) -> str:
    """Return the sequence diagram as a fullscreen-wrapped ``.. uml::`` block.

    Returns an empty string when ``tm.seq()`` produces no content.
    The section heading lives in ``report_template.rst``.
    """
    seq = tm.seq()
    if not seq or not seq.strip():
        return ""
    seq = _wrap_seq_participant_labels(seq)
    seq = seq.replace(
        "@startuml\n",
        "@startuml\nskinparam defaultFontSize 16\n",
        1,
    )
    return _uml_diagram(seq)


def run_model(
    build_model_fn: Callable[[], Any],
    controls: list[Control],
    responses: list[ThreatResponse],
) -> None:
    """Run a threat model from a ``__main__`` entry point.

    Calls *build_model_fn* then either renders a report (when ``--report
    <template>`` is on the command line) or runs the default pytm processing.
    """
    tm = build_model_fn()
    if "--report" in sys.argv:
        _idx = sys.argv.index("--report")
        if _idx + 1 >= len(sys.argv) or sys.argv[_idx + 1].startswith("-"):
            script = os.path.basename(sys.argv[0])
            print(f"Usage: python {script} --report <template_path>", file=sys.stderr)
            raise SystemExit(1)
        tm.resolve()
        title = tm.name
        print(title)
        print("=" * len(title))
        print()
        rendered = tm.report(sys.argv[_idx + 1])
        rendered = rendered.replace("{dfd_content}", _render_dfd_section(tm))
        rendered = rendered.replace("{seq_content}", _render_seq_section(tm))
        rendered = rendered.replace(
            "{assets_rows}", _render_asset_rows(tm, controls, responses)
        )
        rendered = rendered.replace(
            "{threats_rows}", _render_threat_rows(tm, controls, responses)
        )
        rendered = rendered.replace("{controls_rows}", _render_control_rows(controls))
        print(rendered)
    else:
        tm.process()
