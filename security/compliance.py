"""CRA Compliance Track B for dfetch.

Produces an OSCAL 1.1.2 Component Definition and a human-readable RST document
that map the CRA Annex I essential requirements through prEN 40000-1-4 Security
Objectives to dfetch's implemented controls.

Three-tier traceability:
  CRA ECR-a … ECR-m  →  prEN 40000-1-4 SO.*  →  dfetch control C-xxx

Run::

    python -m security.compliance \\
        --component security/dfetch.component-definition.json \\
        --rst > doc/explanation/compliance_track.rst
"""

import argparse
import importlib
import json
import os
import sys
import uuid
from datetime import date
from typing import Any

from security.compliance_data import (
    CLASSIFICATION_DECISION,
    PART_II_REQUIREMENTS,
    SO_IMPLEMENTATIONS,
    STANDARDS,
    TRACK_B_CONTROLS,
    Control,
    SOImplementation,
)

CATALOG_PATH = os.path.join(
    os.path.dirname(__file__), "cra_pren_4000014_oscal_catalog.json"
)

_UUID_NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # uuid.NAMESPACE_URL

_STATUS_LABEL: dict[str, str] = {
    "implemented": "✓ Implemented",
    "partially-implemented": "⚠ Partial",
    "planned": "○ Planned",
    "not-applicable": "— N/A",
}


def _u(key: str) -> str:
    """Return deterministic UUID v5 for the given stable key."""
    return str(uuid.uuid5(_UUID_NS, f"dfetch-cra-{key}"))


def _so_title(so_id: str) -> str:
    """Derive SO.* display name from so-id slug."""
    parts = so_id.removeprefix("so-").split("-")
    # Strip single-letter ECR disambiguation suffix (e.g. -e, -m)
    if len(parts) > 1 and len(parts[-1]) == 1 and parts[-1].isalpha():
        parts = parts[:-1]
    return "SO." + "".join(p.capitalize() for p in parts)


def _load_track_a_controls() -> list[Control]:
    """Load Track A controls from threat models if pytm is available."""
    try:
        tm_sc = importlib.import_module("security.tm_supply_chain")
        tm_u = importlib.import_module("security.tm_usage")
    except ImportError:
        print(
            "Note: pytm not available — Track A controls omitted from control register.",
            file=sys.stderr,
        )
        return []
    sc_controls: list[Any] = getattr(tm_sc, "CONTROLS", [])
    u_controls: list[Any] = getattr(tm_u, "CONTROLS", [])
    return [
        Control(id=c.id, name=c.name, description=c.description, reference=c.reference)
        for c in sc_controls + u_controls
    ]


def get_all_controls() -> list[Control]:
    """Return merged, deduplicated, sorted control register from both tracks."""
    track_a = _load_track_a_controls()
    seen: set[str] = set()
    merged: list[Control] = []
    for ctrl in track_a + TRACK_B_CONTROLS:
        if ctrl.id not in seen:
            seen.add(ctrl.id)
            merged.append(ctrl)
    return sorted(merged, key=lambda c: c.id)


def load_catalog() -> Any:
    """Load the prEN 40000-1-4 OSCAL catalog JSON."""
    with open(CATALOG_PATH, encoding="utf-8") as catalog_file:
        return json.load(catalog_file)


# ── OSCAL Component Definition builder ────────────────────────────────────────


def _build_metadata(version: str) -> dict[str, Any]:
    """Return the OSCAL metadata block."""
    return {
        "title": "dfetch CRA Compliance Component Definition",
        "last-modified": f"{date.today().isoformat()}T00:00:00Z",
        "version": version,
        "oscal-version": "1.1.2",
        "props": [
            {
                "name": "cra-class",
                "value": "Non-commercial OSS — Recital 18 exemption",
            },
            {
                "name": "cra-article",
                "value": (
                    "Article 3(14), Recital 18, Article 13(5) "
                    "of Regulation (EU) 2024/2847"
                ),
            },
            {
                "name": "standard",
                "value": (
                    "prEN 40000-1-4 (draft, indicative publication October 2027)"
                ),
            },
        ],
        "remarks": (
            "Produced voluntarily under Article 13(5) to support downstream integrators. "
            "dfetch is non-commercial open-source software and is not subject to "
            "mandatory CRA conformity obligations (Recital 18)."
        ),
    }


def _build_so_props(so_impl: SOImplementation) -> list[dict[str, str]]:
    """Return OSCAL props list for one SOImplementation."""
    props: list[dict[str, str]] = [
        {"name": "implementation-status", "value": so_impl.status}
    ]
    if so_impl.not_applicable:
        props.append(
            {"name": "not-applicable", "value": "; ".join(so_impl.not_applicable)}
        )
    if so_impl.gaps:
        props.append({"name": "gaps", "value": "; ".join(so_impl.gaps)})
    if so_impl.controls:
        props.append({"name": "dfetch-controls", "value": ", ".join(so_impl.controls)})
    return props


def _build_so_description(so_impl: SOImplementation) -> str:
    """Return the statement description for one SOImplementation."""
    parts = []
    if so_impl.description:
        parts.append(so_impl.description)
    if so_impl.gaps:
        parts.append("Gaps: " + "; ".join(so_impl.gaps))
    if so_impl.not_applicable:
        parts.append("Not applicable: " + "; ".join(so_impl.not_applicable))
    return " ".join(parts) if parts else _so_title(so_impl.so_id)


def _build_implemented_requirements() -> list[dict[str, Any]]:
    """Return one implemented-requirement dict per SO."""
    return [
        {
            "uuid": _u(f"req-{so_impl.so_id}"),
            "control-id": so_impl.so_id,
            "props": _build_so_props(so_impl),
            "statements": [
                {
                    "statement-id": f"{so_impl.so_id}-stmt",
                    "uuid": _u(f"stmt-{so_impl.so_id}"),
                    "description": _build_so_description(so_impl),
                }
            ],
        }
        for so_impl in SO_IMPLEMENTATIONS
    ]


def _build_component(version: str) -> dict[str, Any]:
    """Return the dfetch software component block."""
    return {
        "uuid": _u("component-dfetch"),
        "type": "software",
        "title": "dfetch",
        "description": (
            "Python CLI tool for vendoring source-code dependencies from Git, SVN, "
            "or archive files into a project as plain files."
        ),
        "props": [{"name": "software-version", "value": version}],
        "links": [
            {"href": "https://github.com/dfetch-org/dfetch", "rel": "homepage"},
            {"href": "https://pypi.org/project/dfetch/", "rel": "distribution"},
            {
                "href": "security/cra_pren_4000014_oscal_catalog.json",
                "rel": "reference",
                "text": "prEN 40000-1-4 OSCAL Catalog",
            },
        ],
        "control-implementations": [
            {
                "uuid": _u("ctrl-impl-en40000-1-4"),
                "source": "security/cra_pren_4000014_oscal_catalog.json",
                "description": (
                    "Voluntary alignment with prEN 40000-1-4 Security Objectives. "
                    "The catalog organises CRA Annex I Part I essential requirements "
                    "(ECR-a–m) as groups; this component implements the Security "
                    "Objectives (SO.*) within each ECR using dfetch controls (C-001–C-046)."
                ),
                "implemented-requirements": _build_implemented_requirements(),
            }
        ],
    }


def _build_back_matter() -> dict[str, Any]:
    """Return OSCAL back-matter with key resource references."""
    return {
        "resources": [
            {
                "uuid": _u("res-cra"),
                "title": "Cyber Resilience Act — Regulation (EU) 2024/2847",
                "rlinks": [
                    {
                        "href": (
                            "https://eur-lex.europa.eu/legal-content/EN/TXT/"
                            "?uri=CELEX:32024R2847"
                        )
                    }
                ],
            },
            {
                "uuid": _u("res-catalog"),
                "title": "prEN 40000-1-4 OSCAL Catalog (this repository)",
                "rlinks": [{"href": "security/cra_pren_4000014_oscal_catalog.json"}],
            },
            {
                "uuid": _u("res-security-md"),
                "title": "dfetch Security Policy (SECURITY.md)",
                "rlinks": [
                    {
                        "href": (
                            "https://github.com/dfetch-org/dfetch/blob/main/SECURITY.md"
                        )
                    }
                ],
            },
        ]
    }


def build_oscal_component_definition(version: str = "0.14.0") -> dict[str, Any]:
    """Return a complete OSCAL 1.1.2 Component Definition for dfetch."""
    return {
        "component-definition": {
            "uuid": _u("component-definition"),
            "metadata": _build_metadata(version),
            "components": [_build_component(version)],
            "back-matter": _build_back_matter(),
        }
    }


# ── RST renderer ──────────────────────────────────────────────────────────────


def _rst_title(text: str, char: str = "=") -> str:
    """Return an RST title with underline."""
    return f"{text}\n{char * len(text)}\n"


def _rst_list_table(
    headers: list[str],
    rows: list[list[str]],
    widths: list[int] | None = None,
) -> str:
    """Return an RST list-table directive as a string."""
    lines = [".. list-table::", "   :header-rows: 1"]
    if widths:
        lines.append("   :widths: " + " ".join(str(w) for w in widths))
    lines.append("")
    lines.append("   * - " + "\n     - ".join(headers))
    for row in rows:
        lines.append("   * - " + "\n     - ".join(str(c) for c in row))
    lines.append("")
    return "\n".join(lines)


def _render_classification() -> None:
    """Print the Classification Decision section."""
    print(_rst_title("Classification Decision", "-"))
    rows = [[k, v] for k, v in CLASSIFICATION_DECISION.items()]
    print(_rst_list_table(["Criterion", "Decision / Basis"], rows, widths=[25, 75]))


def _render_standards_table() -> None:
    """Print the Applicable Standards table."""
    print(_rst_title("Applicable Standards", "-"))
    rows = [
        [
            s.name,
            s.reference,
            "Yes" if s.applies else "No",
            s.scope_note,
            s.gap_note or "—",
        ]
        for s in STANDARDS
    ]
    print(
        _rst_list_table(
            ["Standard", "Full title", "Applies", "Scope note", "Gap"],
            rows,
            widths=[18, 25, 6, 35, 16],
        )
    )


def _ecr_map_from_catalog() -> dict[str, str]:
    """Return mapping of ECR id → requirement text from the OSCAL catalog."""
    catalog = load_catalog()
    return {
        group["id"]: next(
            (
                p["value"]
                for p in group.get("props", [])
                if p["name"] == "requirement-text"
            ),
            "",
        )
        for group in catalog["catalog"]["groups"]
    }


def _part_i_rows(ecr_map: dict[str, str]) -> list[list[str]]:
    """Build table rows for the Part I ECR table."""
    rows: list[list[str]] = []
    current_ecr = ""
    for so in SO_IMPLEMENTATIONS:
        ecr_cell = ""
        if so.ecr_id != current_ecr:
            current_ecr = so.ecr_id
            ecr_cell = f"**{so.ecr_id.upper()}** — {ecr_map.get(so.ecr_id, '')}"
        ctrls = ", ".join(so.controls) if so.controls else "—"
        gaps = "; ".join(so.gaps) if so.gaps else "—"
        rows.append(
            [
                ecr_cell,
                _so_title(so.so_id),
                ctrls,
                gaps,
                _STATUS_LABEL.get(so.status, so.status),
            ]
        )
    return rows


def _render_part_i_table() -> None:
    """Print the Part I security requirements table."""
    print(_rst_title("Part I — Product Security Requirements (ECR-a to ECR-m)", "-"))
    print(
        "The table below summarises dfetch's implementation of each prEN 40000-1-4 "
        "Security Objective per CRA essential requirement.\n"
    )
    print(
        _rst_list_table(
            ["CRA ECR", "SO (prEN 40000-1-4)", "dfetch controls", "Gaps", "Status"],
            _part_i_rows(_ecr_map_from_catalog()),
            widths=[20, 28, 18, 20, 14],
        )
    )


def _render_part_ii_table() -> None:
    """Print the Part II vulnerability handling table."""
    print(_rst_title("Part II — Vulnerability Handling (prEN 40000-1-3)", "-"))
    print(
        "Part II requirements are addressed via prEN 40000-1-3. "
        "pii-04 is not applicable under Recital 18.\n"
    )
    rows = [
        [
            req.ref,
            req.text,
            ", ".join(req.controls) if req.controls else "—",
            "; ".join(req.gaps) if req.gaps else "—",
            _STATUS_LABEL.get(req.status, req.status),
        ]
        for req in PART_II_REQUIREMENTS
    ]
    print(
        _rst_list_table(
            ["CRA ref", "Requirement", "dfetch controls", "Gaps", "Status"],
            rows,
            widths=[10, 32, 18, 24, 12],
        )
    )


def _gap_entries() -> list[tuple[str, str]]:
    """Return (title, body) pairs for the gap analysis section."""
    return [
        (
            "C-043 — Release-gate CVE check"
            + " (ECR-a, SO.VulnerabilityManagementProcess → GEC-1)",
            (
                "dfetch's CI detects vulnerabilities at commit time (C-015, C-016, C-017) "
                "but does not gate the release publish on a CVE scan of runtime dependencies. "
                "C-043 (planned) adds ``pip-audit`` or ``osv-scanner`` to the publish "
                "workflow."
            ),
        ),
        (
            "C-044 — Data minimisation policy"
            + " (ECR-g, SO.DataMinimization → DTM-1)",
            (
                "dfetch processes dependency metadata only. The ``.dfetch_data.yaml`` file "
                "stores: ``remote_url`` (credentials stripped by C-036), ``revision``, "
                "optional ``integrity.hash``, and ``last_fetch`` timestamp. Each field is "
                "functionally necessary for ``dfetch check`` and ``dfetch freeze``. "
                "No personal data is collected; no telemetry is sent. "
                "C-044 formalises this assertion as a documented policy."
            ),
        ),
        (
            "C-046 — Exploit mitigation inventory"
            + " (ECR-k, SO.ReduceImpactOfIncident → GEC-11)",
            (
                "prEN 40000-1-4 ECR-k requires documenting applicable exploit mitigation "
                "techniques. For dfetch (pure Python):\n\n"
                "- **ASLR / DEP / stack canaries**: provided by CPython and the OS; "
                "  not in dfetch's control but inherited.\n"
                "- **No eval/exec of remote content**: dfetch never evaluates fetched "
                "  content as code.\n"
                "- **Constant-time comparison** (C-005): HMAC-based integrity hash uses "
                "  ``hmac.compare_digest``.\n"
                "- **No shell injection** (C-007): all subprocess calls use ``shell=False``.\n"
                "- **Input validation** (C-008): URL scheme, path, and revision inputs "
                "  are validated.\n"
                "- **Static analysis** (C-015, C-017): CodeQL and bandit gate every commit.\n"
                "- CFI, sandboxing, and signed-execution policies are not applicable to "
                "  a pure-Python tool."
            ),
        ),
    ]


def _render_gap_analysis() -> None:
    """Print the Gap Analysis section."""
    print(_rst_title("Gap Analysis — Compliance-Only Controls", "-"))
    entries = _gap_entries()
    print(
        f"{len(entries)} compliance-only controls address CRA requirements not "
        "independently covered by the Track A risk models.\n"
    )
    for title, body in entries:
        print(f"**{title}**\n")
        print(f"{body}\n")


def _render_control_register() -> None:
    """Print the final merged control register table."""
    print(_rst_title("Final Control Register", "-"))
    print(
        "All controls from Track A (risk-driven) and Track B (regulatory) merged and "
        "sorted. Track B controls (C-043–C-046) are marked accordingly.\n"
    )
    track_b_ids = {c.id for c in TRACK_B_CONTROLS}
    rows = [
        [
            ctrl.id,
            ctrl.name,
            "Track B" if ctrl.id in track_b_ids else "Track A",
            ctrl.reference or "—",
        ]
        for ctrl in get_all_controls()
    ]
    print(
        _rst_list_table(
            ["ID", "Name", "Track", "Reference"],
            rows,
            widths=[8, 40, 10, 42],
        )
    )


def render_rst() -> None:
    """Print the full compliance track RST document to stdout."""
    print(".. _compliance_track:\n")
    print(_rst_title("CRA Compliance Track B"))
    print(
        ".. note::\n\n"
        "   dfetch is **non-commercial open-source software** and is exempt from\n"
        "   mandatory CRA obligations under Recital 18 of Regulation (EU) 2024/2847.\n"
        "   This document is produced voluntarily under Article 13(5) to support\n"
        "   downstream integrators who must account for open-source components in\n"
        "   their own conformity assessments.\n"
    )
    print(
        "Three-tier traceability::\n\n"
        "   CRA Annex I Essential Requirement (ECR-a … ECR-m)\n"
        "           ↓\n"
        "   prEN 40000-1-4 Security Objective (SO.*)\n"
        "           ↓\n"
        "   dfetch control (C-001 … C-046) or documented gap\n"
    )
    print(
        "Machine-readable OSCAL 1.1.2 artifacts are kept alongside the source:\n\n"
        "- ``security/cra_pren_4000014_oscal_catalog.json`` — prEN 40000-1-4 catalog\n"
        "- ``security/dfetch.component-definition.json`` — dfetch Component Definition\n"
    )
    _render_classification()
    _render_standards_table()
    _render_part_i_table()
    _render_part_ii_table()
    _render_gap_analysis()
    _render_control_register()
    print(_rst_title("OSCAL Artifacts", "-"))
    print(
        "The OSCAL 1.1.2 Component Definition references the catalog file and can be\n"
        "regenerated with:\n\n"
        ".. code-block:: bash\n\n"
        "   python -m security.compliance \\\\\n"
        "       --component security/dfetch.component-definition.json \\\\\n"
        "       --rst > doc/explanation/compliance_track.rst\n"
    )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate CRA Compliance Track B artifacts"
    )
    parser.add_argument(
        "--component", metavar="FILE", help="Write OSCAL Component Definition JSON"
    )
    parser.add_argument(
        "--rst", action="store_true", help="Print RST document to stdout"
    )
    parser.add_argument(
        "--version", default="0.14.0", help="dfetch version (default: 0.14.0)"
    )
    args = parser.parse_args()

    if args.component:
        comp_def = build_oscal_component_definition(version=args.version)
        with open(args.component, "w", encoding="utf-8") as fh:
            json.dump(comp_def, fh, indent=2)
        print(f"Written: {args.component}", file=sys.stderr)

    if args.rst:
        render_rst()
