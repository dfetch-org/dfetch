"""CRA Compliance Track B for dfetch.

Produces an OSCAL 1.2.2 Component Definition and a human-readable RST document
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
import re
import sys
import uuid
from datetime import date
from typing import Any

from security.compliance_data import (
    ANNEX_V_MAP,
    CLASSIFICATION_DECISION,
    PART_II_REQUIREMENTS,
    SO_IMPLEMENTATIONS,
    STANDARDS,
    TRACK_A_CONTROLS,
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


_GITHUB_BASE = "https://github.com/dfetch-org/dfetch"


def _load_track_a_controls(track_b_only: bool = False) -> list[Control]:
    """Load Track A controls from threat models if pytm is available."""
    try:
        tm_sc = importlib.import_module("security.tm_supply_chain")
        tm_u = importlib.import_module("security.tm_usage")
    except ModuleNotFoundError:
        if not track_b_only:
            print(
                "Note: pytm not available — using static Track A controls.",
                file=sys.stderr,
            )
        return list(TRACK_A_CONTROLS)
    sc_controls: list[Any] = getattr(tm_sc, "CONTROLS", [])
    u_controls: list[Any] = getattr(tm_u, "CONTROLS", [])
    return [
        Control(id=c.id, name=c.name, description=c.description, reference=c.reference)
        for c in sc_controls + u_controls
    ]


def get_all_controls(track_b_only: bool = False) -> list[Control]:
    """Return merged, deduplicated, sorted control register from both tracks."""
    track_a = _load_track_a_controls(track_b_only=track_b_only)
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


_PARTY_UUID_DFETCH_ORG = _u("party-dfetch-org")


def _build_metadata(version: str) -> dict[str, Any]:
    """Return the OSCAL 1.2.2 metadata block with parties and roles."""
    return {
        "title": "dfetch CRA Compliance Component Definition",
        "last-modified": f"{date.today().isoformat()}T00:00:00Z",
        "version": version,
        "oscal-version": "1.2.2",
        "document-ids": [
            {
                "scheme": "uri",
                "identifier": (
                    "https://github.com/dfetch-org/dfetch/blob/main/"
                    "security/dfetch.component-definition.json"
                ),
            }
        ],
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
            {
                "name": "openssf-scorecard",
                "value": "https://api.securityscorecards.dev/projects/github.com/dfetch-org/dfetch",
            },
        ],
        "roles": [
            {
                "id": "supplier",
                "title": "Software Supplier",
                "description": "Organisation that develops and distributes dfetch.",
            },
            {
                "id": "maintainer",
                "title": "Maintainer",
                "description": "Primary maintainer of the dfetch project and this compliance document.",
            },
        ],
        "parties": [
            {
                "uuid": _PARTY_UUID_DFETCH_ORG,
                "type": "organization",
                "name": "dfetch-org",
                "links": [
                    {
                        "href": "https://github.com/dfetch-org",
                        "rel": "homepage",
                    }
                ],
                "remarks": (
                    "Non-commercial open-source organisation. "
                    "dfetch is not placed on the market in the context of a commercial activity."
                ),
            }
        ],
        "responsible-parties": [
            {
                "role-id": "supplier",
                "party-uuids": [_PARTY_UUID_DFETCH_ORG],
            },
            {
                "role-id": "maintainer",
                "party-uuids": [_PARTY_UUID_DFETCH_ORG],
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


def _build_evidence_links(so_impl: SOImplementation) -> list[dict[str, str]]:
    """Return OSCAL links pointing to code or CI evidence for one SO."""
    return [
        {"href": href, "rel": "evidence", "text": text}
        for href, text in so_impl.evidence_hrefs
    ]


def _build_implemented_requirements() -> list[dict[str, Any]]:
    """Return one implemented-requirement dict per SO."""
    reqs = []
    for so_impl in SO_IMPLEMENTATIONS:
        req: dict[str, Any] = {
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
        links = _build_evidence_links(so_impl)
        if links:
            req["links"] = links
        reqs.append(req)
    return reqs


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
        "purpose": (
            "Vendor source-code dependencies from Git, SVN, or archive files into a "
            "project as plain files, enabling reproducible builds without submodules or "
            "externals. Supports integrity hashing, plaintext-transport detection, and "
            "credential redaction to reduce supply-chain risk."
        ),
        "props": [
            {"name": "software-version", "value": version},
            {"name": "asset-type", "value": "software.application"},
            {"name": "vendor-name", "value": "dfetch-org"},
            {"name": "license", "value": "MIT"},
        ],
        "links": [
            {"href": "https://github.com/dfetch-org/dfetch", "rel": "homepage"},
            {"href": "https://pypi.org/project/dfetch/", "rel": "distribution"},
            {
                "href": "security/cra_pren_4000014_oscal_catalog.json",
                "rel": "reference",
                "text": "prEN 40000-1-4 OSCAL Catalog",
            },
            {
                "href": "SECURITY.md",
                "rel": "reference",
                "text": "Vulnerability Disclosure Policy",
            },
        ],
        "responsible-roles": [
            {
                "role-id": "supplier",
                "party-uuids": [_PARTY_UUID_DFETCH_ORG],
            }
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
                "title": "dfetch Vulnerability Disclosure Policy (SECURITY.md)",
                "rlinks": [
                    {
                        "href": (
                            "https://github.com/dfetch-org/dfetch/blob/main/SECURITY.md"
                        )
                    }
                ],
            },
            {
                "uuid": _u("res-scorecard"),
                "title": "OpenSSF Scorecard — dfetch supply-chain security score",
                "props": [
                    {"name": "type", "value": "assessment-report"},
                    {"name": "tool", "value": "OpenSSF Scorecard"},
                ],
                "rlinks": [
                    {
                        "href": (
                            "https://api.securityscorecards.dev/projects/"
                            "github.com/dfetch-org/dfetch"
                        )
                    }
                ],
            },
            {
                "uuid": _u("res-scorecard-workflow"),
                "title": "OpenSSF Scorecard CI workflow",
                "rlinks": [
                    {
                        "href": ".github/workflows/scorecard.yml",
                    }
                ],
            },
            {
                "uuid": _u("res-slsa-provenance"),
                "title": "SLSA Source Provenance Attestation workflow",
                "props": [
                    {"name": "type", "value": "attestation"},
                    {"name": "framework", "value": "SLSA"},
                ],
                "rlinks": [
                    {
                        "href": ".github/workflows/source-provenance.yml",
                    }
                ],
            },
            {
                "uuid": _u("res-sigstore-attestation"),
                "title": "Sigstore build provenance and SBOM attestation workflow",
                "props": [
                    {"name": "type", "value": "attestation"},
                    {"name": "framework", "value": "Sigstore"},
                ],
                "rlinks": [
                    {
                        "href": ".github/workflows/python-publish.yml",
                    }
                ],
            },
            {
                "uuid": _u("res-in-toto-attestation"),
                "title": "in-toto test-results attestation workflow",
                "props": [
                    {"name": "type", "value": "attestation"},
                    {"name": "framework", "value": "in-toto"},
                ],
                "rlinks": [
                    {
                        "href": ".github/workflows/test.yml",
                    }
                ],
            },
            {
                "uuid": _u("res-codeql"),
                "title": "CodeQL static analysis workflow (C-015)",
                "props": [
                    {"name": "type", "value": "tool"},
                    {"name": "tool", "value": "CodeQL"},
                ],
                "rlinks": [
                    {
                        "href": ".github/workflows/codeql-analysis.yml",
                    }
                ],
            },
            {
                "uuid": _u("res-dep-review"),
                "title": "Dependency review workflow (C-016)",
                "props": [
                    {"name": "type", "value": "tool"},
                    {"name": "tool", "value": "dependency-review"},
                ],
                "rlinks": [
                    {
                        "href": ".github/workflows/dependency-review.yml",
                    }
                ],
            },
            {
                "uuid": _u("res-releases"),
                "title": "dfetch GitHub Releases (SBOM and attestation download)",
                "rlinks": [
                    {
                        "href": "https://github.com/dfetch-org/dfetch/releases",
                    }
                ],
            },
            {
                "uuid": _u("res-verify-integrity"),
                "title": "How to verify dfetch integrity and attestations",
                "rlinks": [
                    {
                        "href": (
                            "https://dfetch.readthedocs.io/en/latest/howto/verify-integrity.html"
                        )
                    }
                ],
            },
        ]
    }


def build_oscal_component_definition(version: str = "0.14.0") -> dict[str, Any]:
    """Return a complete OSCAL 1.2.2 Component Definition for dfetch."""
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


def _rst_escape_star(text: str) -> str:
    """Escape standalone * in RST cell text without touching **bold** markup."""
    return re.sub(r"(?<!\*)\*(?!\*)", r"\\*", text)


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
    lines.append("   * - " + "\n     - ".join(_rst_escape_star(h) for h in headers))
    for row in rows:
        lines.append("   * - " + "\n     - ".join(str(c) for c in row))
    lines.append("")
    return "\n".join(lines)


def _rst_ctrl_ref(ctrl_id: str) -> str:
    """Return an RST cross-reference for a control ID."""
    return f":ref:`{ctrl_id} <{ctrl_id.lower()}>`"


def _format_ref_as_rst(ref: str) -> str:
    """Convert a control reference string to RST markup.

    Handles: empty/dash, doc/ paths, glob patterns, directories, comma-separated,
    and regular file paths — all converted to appropriate GitHub links or RST refs.
    """
    ref = ref.strip()
    if not ref or ref == "—":
        return "—"
    # Already RST markup
    if ref.startswith(":doc:") or ref.startswith(":ref:"):
        return ref
    # Handle parenthetical suffix like "path (note about it)"
    paren_suffix = ""
    if " (" in ref and ref.endswith(")"):
        paren_idx = ref.rfind(" (")
        paren_suffix = " " + ref[paren_idx + 1 :]
        ref = ref[:paren_idx]
    # doc/ prefix → RST :doc: reference (relative to doc/explanation/)
    if ref.startswith("doc/howto/"):
        slug = ref.removeprefix("doc/howto/").removesuffix(".rst")
        return f":doc:`../howto/{slug}`"
    if ref.startswith("doc/explanation/"):
        slug = ref.removeprefix("doc/explanation/").removesuffix(".rst")
        return f":doc:`{slug}`"
    # Comma-separated → format each individually
    if "," in ref:
        parts = [_format_single_ref(p.strip()) for p in ref.split(",")]
        return ",\n       ".join(parts)
    return _format_single_ref(ref) + paren_suffix


def _format_single_ref(ref: str) -> str:
    """Format a single (non-comma-separated) file/dir reference as RST."""
    ref = ref.strip()
    if not ref:
        return "—"
    # Glob or directory → tree link
    if ref.endswith("/") or "*" in ref:
        base = ref.rstrip("/").rstrip("*").rstrip("/").rstrip(".")
        tree_url = f"{_GITHUB_BASE}/tree/main/{base}"
        display = ref
        return f"`{display} <{tree_url}>`_"
    # Regular file → blob link
    blob_url = f"{_GITHUB_BASE}/blob/main/{ref}"
    return f"`{ref} <{blob_url}>`_"


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
        ctrls = ", ".join(_rst_ctrl_ref(c) for c in so.controls) if so.controls else "—"
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

    def _fmt_ctrl(c: str) -> str:
        if re.match(r"^C-\d+$", c):
            return _rst_ctrl_ref(c)
        if c == "SECURITY.md":
            return f"`SECURITY.md <{_GITHUB_BASE}/blob/main/SECURITY.md>`_"
        return c

    rows = [
        [
            req.ref,
            req.text,
            ", ".join(_fmt_ctrl(c) for c in req.controls) if req.controls else "—",
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
            ":ref:`C-043 <c-043>` — Release-gate CVE check"
            " (ECR-a, SO.VulnerabilityManagementProcess → GEC-1)",
            (
                "dfetch's CI detects vulnerabilities at commit time "
                "(:ref:`C-015 <c-015>`, :ref:`C-016 <c-016>`, :ref:`C-017 <c-017>`). "
                ":ref:`C-043 <c-043>` completes the coverage: the publish workflow runs "
                "``pip-audit`` against the project's runtime dependencies via the OSV "
                "database and blocks the release if any known vulnerability is found."
            ),
        ),
        (
            ":ref:`C-044 <c-044>` — Data minimisation policy"
            " (ECR-g, SO.DataMinimization → DTM-1)",
            (
                "dfetch processes dependency metadata only. The ``.dfetch_data.yaml`` "
                "file stores: ``remote_url`` (credentials stripped by "
                ":ref:`C-036 <c-036>`), ``revision``, optional ``integrity.hash``, "
                "and ``last_fetch`` timestamp. Each field is functionally necessary "
                "for ``dfetch check`` and ``dfetch freeze``. No personal data is "
                "collected; no telemetry is sent. :ref:`C-044 <c-044>` formalises "
                "this assertion as a documented policy."
            ),
        ),
        (
            ":ref:`C-046 <c-046>` — Exploit mitigation inventory"
            " (ECR-k, SO.ReduceImpactOfIncident → GEC-11)",
            (
                "prEN 40000-1-4 ECR-k requires documenting applicable exploit "
                "mitigation techniques. For dfetch (pure Python):\n\n"
                "- **ASLR / DEP / stack canaries**: provided by CPython and the OS; "
                "  not in dfetch's control but inherited.\n"
                "- **No eval/exec of remote content**: dfetch never evaluates fetched "
                "  content as code.\n"
                "- **Constant-time comparison** (:ref:`C-005 <c-005>`): HMAC-based "
                "  integrity hash uses ``hmac.compare_digest``.\n"
                "- **No shell injection** (:ref:`C-007 <c-007>`): all subprocess "
                "  calls use ``shell=False``.\n"
                "- **Input validation** (:ref:`C-008 <c-008>`): URL scheme, path, "
                "  and revision inputs are validated.\n"
                "- **Static analysis** (:ref:`C-015 <c-015>`, :ref:`C-017 <c-017>`): "
                "  CodeQL and bandit gate every commit.\n"
                "- CFI, sandboxing, and signed-execution policies are not applicable "
                "  to a pure-Python tool."
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


def _render_annex_v() -> None:
    """Print the CRA Annex V technical documentation map."""
    print(_rst_title("CRA Annex V — Technical Documentation Map", "-"))
    print(
        "Annex V of Regulation (EU) 2024/2847 specifies the minimum content for "
        "a manufacturer's technical documentation. The table below maps each "
        "Annex V element to the corresponding dfetch artifact or section.\n"
        "Because dfetch is outside mandatory CRA scope, this mapping is provided "
        "as a convenience for downstream integrators conducting their own "
        "Article 13 conformity assessments.\n"
    )
    print(
        _rst_list_table(
            ["Annex V element", "dfetch artifact / section"],
            [[elem, artifact] for elem, artifact in ANNEX_V_MAP],
            widths=[45, 55],
        )
    )


def _render_impl_notes() -> None:
    """Print notes on 'Implemented' rows that have no control assigned."""
    noted = [so for so in SO_IMPLEMENTATIONS if so.note]
    if not noted:
        return
    print('.. rubric:: Notes on "Implemented" rows\n')
    for so in noted:
        print(so.note + "\n")


def render_rst(track_b_only: bool = False) -> None:
    """Print the full compliance track RST document to stdout."""
    print(
        ".. This file is auto-generated by ``python -m security.compliance --rst``.\n"
        "   Do not edit manually — edit security/compliance_data.py instead.\n"
    )
    print(".. _compliance_track:\n")
    print(_rst_title("CRA Compliance"))
    print(
        ".. note::\n\n"
        "   dfetch is **non-commercial open-source software** and falls outside the\n"
        "   mandatory scope of Regulation (EU) 2024/2847 (CRA): it is not placed on\n"
        "   the market in the context of a commercial activity (CRA Article 3(1);\n"
        "   Recital 18 provides interpretive context). This document is produced\n"
        "   voluntarily to support downstream integrators who must account for\n"
        "   open-source components in their own Article 13 conformity assessments.\n"
    )
    print(
        "This page provides three-tier traceability from the CRA Annex I essential\n"
        "requirements through the prEN 40000-1-4 Security Objectives to the\n"
        "concrete dfetch controls or documented gaps::\n\n"
        "   CRA Annex I Essential Requirement (ECR-a … ECR-m)\n"
        "           ↓\n"
        "   prEN 40000-1-4 Security Objective (SO.*)\n"
        "           ↓\n"
        "   dfetch control (C-001 … C-046) or documented gap\n"
    )
    print(
        "Machine-readable artifacts are kept alongside the source, encoded in "
        "OSCAL 1.2.2:\n\n"
        "- `security/cra_pren_4000014_oscal_catalog.json"
        " <https://github.com/dfetch-org/dfetch/blob/main/"
        "security/cra_pren_4000014_oscal_catalog.json>`_"
        " — prEN 40000-1-4 catalog (includes parties, roles, and responsible-parties)\n"
        "- `security/dfetch.component-definition.json"
        " <https://github.com/dfetch-org/dfetch/blob/main/"
        "security/dfetch.component-definition.json>`_"
        " — dfetch Component Definition (includes supplier party, purpose, evidence"
        " links per implemented-requirement)\n"
    )
    print(
        "The full list of all controls is available on the :doc:`control_register` page.\n"
    )
    print(
        ".. rubric:: Status key\n\n"
        ".. list-table::\n"
        "   :widths: 10 90\n\n"
        "   * - ✓\n"
        "     - Implemented — control satisfies the objective fully.\n"
        "   * - ⚠\n"
        "     - Partial — control exists but a gap remains (see Gaps column).\n"
        "   * - N/A\n"
        "     - Not applicable — the objective does not apply to dfetch.\n"
    )
    print("----\n")
    _render_classification()
    print("----\n")
    _render_annex_v()
    print("----\n")
    _render_standards_table()
    print("----\n")
    _render_part_i_table()
    _render_impl_notes()
    print("----\n")
    _render_part_ii_table()
    print("----\n")
    _render_gap_analysis()
    print("----\n")
    print(_rst_title("OSCAL Artifacts", "-"))
    print(
        "The OSCAL 1.2.2 Component Definition references the catalog file and can be\n"
        "regenerated with:\n\n"
        ".. code-block:: bash\n\n"
        "   python -m security.compliance \\\\\n"
        "       --component security/dfetch.component-definition.json \\\\\n"
        "       --version 0.15.0 \\\\\n"
        "       --rst > doc/explanation/compliance_track.rst\n"
    )


def render_control_register_rst(track_b_only: bool = False) -> None:
    """Print the control register RST document to stdout."""
    print(
        ".. This file is auto-generated by ``python -m security.compliance "
        "--control-register``.\n"
        "   Do not edit manually — edit security/compliance_data.py or the threat "
        "model files instead.\n"
    )
    print(".. _control_register:\n")
    print(_rst_title("Control Register"))
    print(
        "All controls implemented by dfetch, sorted by ID. Risk-driven controls "
        "emerge from the :doc:`threat models <security>`; compliance-only controls "
        "address CRA requirements not independently surfaced by the risk analysis.\n"
    )
    track_b_ids = {c.id for c in TRACK_B_CONTROLS}
    controls = get_all_controls(track_b_only=track_b_only)

    # Build RST list-table rows with anchors inside the ID cell
    lines = [".. list-table::", "   :header-rows: 1", "   :widths: 8 40 16 36", ""]
    lines.append("   * - ID\n     - Name\n     - Type\n     - Reference")
    for ctrl in controls:
        ctrl_type = "Compliance-only" if ctrl.id in track_b_ids else "Risk-driven"
        ref_rst = _format_ref_as_rst(ctrl.reference)
        anchor = ctrl.id.lower()
        # RST anchor in table cell must be followed by blank line then the cell text
        id_cell = f".. _{anchor}:\n\n       {ctrl.id}"
        lines.append(
            f"   * - {id_cell}\n"
            f"     - {ctrl.name}\n"
            f"     - {ctrl_type}\n"
            f"     - {ref_rst}"
        )
    lines.append("")
    print("\n".join(lines))


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
        "--control-register",
        action="store_true",
        help="Print control register RST document to stdout",
    )
    parser.add_argument(
        "--version", default="0.14.0", help="dfetch version (default: 0.14.0)"
    )
    parser.add_argument(
        "--track-b-only",
        action="store_true",
        help=(
            "Omit Track A controls when pytm is not installed instead of failing. "
            "Must be set explicitly to allow degraded output."
        ),
    )
    args = parser.parse_args()

    if args.component:
        comp_def = build_oscal_component_definition(version=args.version)
        with open(args.component, "w", encoding="utf-8") as fh:
            json.dump(comp_def, fh, indent=2)
        print(f"Written: {args.component}", file=sys.stderr)

    if args.rst:
        render_rst(track_b_only=args.track_b_only)

    if args.control_register:
        render_control_register_rst(track_b_only=args.track_b_only)
