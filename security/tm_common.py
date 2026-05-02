"""Shared building blocks for the dfetch threat models.

Both supply-chain and usage models import from here.  No pytm objects at
module level, so it is safe to import before ``TM.reset()``.
"""

import html
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from pytm import Assumption, Boundary, Data, Element
from pytm.report_util import ReportUtils

THREATS_FILE = os.path.join(os.path.dirname(__file__), "threats.json")


@dataclass
class ControlAssessment:
    """Implementation state and risk classification for a control."""

    status: Literal["implemented", "planned", "gap"] = "implemented"
    risk: Literal["Critical", "High", "Medium", "Low"] = "Medium"
    stride: list[str] = field(default_factory=list)


@dataclass
class Control:
    """A security control or known gap against a specific threat."""

    id: str
    name: str
    description: str
    assets: list[str] = field(default_factory=list)
    threats: list[str] = field(default_factory=list)
    reference: str = ""
    assessment: ControlAssessment = field(default_factory=ControlAssessment)

    @property
    def status(self) -> str:
        """Delegation to assessment.status for backwards-compatible access."""
        return self.assessment.status

    def to_pytm(self) -> str:
        """Return a human-readable label used in traceability comments."""
        return f"[{self.id}] {self.name}"


def build_asset_controls_index(
    controls: list[Control],
    valid_asset_ids: set[str],
) -> dict[str, list[Control]]:
    """Return an asset-ID → control list mapping built from *controls*."""
    index: dict[str, list[Control]] = {}
    for ctrl in controls:
        for asset_id in ctrl.assets:
            if asset_id not in valid_asset_ids:
                raise ValueError(
                    f"Unknown asset ID '{asset_id}' in control '{ctrl.id}: {ctrl.name}'"
                )
            index.setdefault(asset_id, []).append(ctrl)
    return index


# ── Shared trust-boundary factories ─────────────────────────────────────────
#
# Called *after* TM.reset() in each model so the created Boundary objects
# register with the correct TM singleton.


def make_dev_env_boundary() -> Boundary:
    """Create the *Local Developer Environment* trust boundary."""
    b = Boundary("Local Developer Environment")
    b.description = (
        "Developer workstation or local CI runner.  Assumed trusted at invocation "
        "time.  Hosts the manifest (``dfetch.yaml``), vendor directory, dependency "
        "metadata (``.dfetch_data.yaml``), and patch files."
    )
    return b


def make_network_boundary(description: str | None = None) -> Boundary:
    """Create the *Internet* trust boundary."""
    b = Boundary("Internet")
    b.description = description or (
        "All traffic crossing the local/remote boundary.  TLS enforcement is the "
        "responsibility of the OS and VCS clients; dfetch does not enforce HTTPS "
        "on manifest URLs."
    )
    return b


# ── Assumption factories ─────────────────────────────────────────────────────


def make_supply_chain_assumptions() -> list[Assumption]:
    """Return the ``Assumption`` objects scoped to the supply-chain model."""
    return [
        Assumption(
            "Trusted workstation",
            description=(
                "Developer workstations are trusted at development and commit time.  "
                "A compromised workstation is outside the scope of this model."
            ),
        ),
        Assumption(
            "CI runner posture",
            description=(
                "GitHub Actions environments inherit the security posture of the "
                "GitHub-hosted runner.  Ephemeral runner isolation is provided by GitHub."
            ),
        ),
        Assumption(
            "Harden-runner in block mode",
            description=(
                "The ``harden-runner`` egress policy is set to ``block`` with an "
                "allowlist of permitted endpoints.  Outbound network connections from "
                "CI runners are blocked unless explicitly permitted."
            ),
        ),
        Assumption(
            "Build deps without hash pinning",
            description=(
                "dfetch's own build and dev dependencies are installed without "
                "``--require-hashes``, so a compromised PyPI mirror can substitute "
                "malicious build tools."
            ),
        ),
    ]


def make_usage_assumptions() -> list[Assumption]:
    """Return the ``Assumption`` objects scoped to the runtime-usage model."""
    return [
        Assumption(
            "Trusted workstation",
            description=(
                "Developer workstations are trusted at dfetch invocation time.  "
                "A compromised workstation is outside the scope of this threat model."
            ),
        ),
        Assumption(
            "TLS delegated to client",
            description=(
                "TLS certificate validation is delegated to the OS trust store and the "
                "git / svn / urllib clients.  dfetch does not independently validate "
                "certificates."
            ),
        ),
        Assumption(
            "No persisted secrets",
            description=(
                "No runtime secrets are persisted to disk by dfetch itself.  "
                "VCS credentials are managed by the OS keychain, SSH agent, or CI "
                "secret store."
            ),
        ),
        Assumption(
            "Optional integrity hash",
            description=(
                "The ``integrity.hash`` field in the manifest is optional.  Archive "
                "dependencies without it have no content-authenticity guarantee beyond "
                "TLS transport, which is itself absent for plain ``http://`` URLs."
            ),
        ),
        Assumption(
            "Mutable VCS references",
            description=(
                "Branch- and tag-pinned Git dependencies are mutable references.  "
                "Upstream force-pushes silently change what is fetched without "
                "triggering a manifest diff."
            ),
        ),
        Assumption(
            "Manifest under code review",
            description=(
                "The manifest (``dfetch.yaml``) is under version control and subject to "
                "code review.  An adversary with write access to the manifest can redirect "
                "fetches to attacker-controlled sources; this threat is addressed at the "
                "code-review boundary, not within dfetch itself."
            ),
        ),
        Assumption(
            "dfetch scope boundary",
            description=(
                "dfetch is responsible only for its own security posture.  The security "
                "of fetched third-party source code is the responsibility of the manifest "
                "author who selects and pins each dependency."
            ),
        ),
        Assumption(
            "No HTTPS enforcement",
            description=(
                "HTTPS enforcement is the responsibility of the manifest author.  dfetch "
                "accepts ``http://``, ``svn://``, and other non-TLS scheme URLs as written "
                "- it does not upgrade or reject them."
            ),
        ),
    ]


def render_controls_section(controls: list[Control]) -> str:
    """Render controls and gaps as a markdown section appended to the report."""
    implemented = [c for c in controls if c.status == "implemented"]
    gaps = [c for c in controls if c.status == "gap"]

    parts: list[str] = []

    def _render_control(c: Control, *, is_gap: bool) -> str:
        meta: list[str] = [f"**Risk:** {c.assessment.risk}"]
        if c.assessment.stride:
            meta.append(f"**STRIDE:** {', '.join(c.assessment.stride)}")
        label = "**Affects threats:**" if is_gap else "**Mitigates:**"
        if c.threats:
            meta.append(f"{label} {', '.join(c.threats)}")
        lines = [f"### {c.id}: {c.name}", "  \n".join(meta)]
        if c.reference:
            lines.append(f"**Reference:** `{c.reference}`")
        lines.append(f"\n{c.description}")
        return "\n".join(lines)

    if implemented:
        parts.append("## Controls\n")
        parts.extend(_render_control(c, is_gap=False) for c in implemented)

    if gaps:
        parts.append("## Gaps\n")
        parts.extend(_render_control(c, is_gap=True) for c in gaps)

    return "\n\n".join(parts)


def _render_finding(f: Any) -> str:
    """Render one pytm Finding to an HTML ``<details>`` block string."""

    def _esc(attr: str) -> str:
        return html.escape(str(getattr(f, attr, "")))

    def _esc_ml(attr: str) -> str:
        return html.escape(str(getattr(f, attr, ""))).replace("\n", "<br>")

    return (
        "<details>\n  <summary>\n    "
        + _esc("threat_id")
        + " - "
        + _esc("description")
        + "\n  </summary>\n  <h6>Targeted Element</h6>\n  <p>"
        + _esc("target")
        + "</p>\n  <h6>Severity</h6>\n  <p>"
        + _esc("severity")
        + "</p>\n  <h6>Example Instances</h6>\n  <p>"
        + _esc_ml("example")
        + "</p>\n  <h6>Mitigations</h6>\n  <p>"
        + _esc_ml("mitigations")
        + "</p>\n  <h6>References</h6>\n  <p>"
        + _esc_ml("references")
        + "</p>\n</details>\n"
    )


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
    to an HTML string directly, so no sub-template is needed in the report.
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
            if not findings:
                return ""
            rendered = "".join(_render_finding(f) for f in findings)
            return "\n**Threats**\n\n" + rendered
        if not isinstance(element, Element) or not element.inScope:
            return ""
        findings = element.findings
        if not findings:
            return ""
        rendered = "".join(_render_finding(f) for f in findings)
        return "\n**Threats**\n\n" + rendered

    ReportUtils.getInScopeFindings = staticmethod(_fixed)


def run_model(build_model_fn: Callable[[], Any], controls: list[Control]) -> None:
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
        print(tm.report(sys.argv[_idx + 1]))
        print(render_controls_section(controls))
    else:
        tm.process()


def make_attacker_profiles() -> list[Assumption]:
    """Return Assumption objects describing the in-scope adversary classes."""
    return [
        Assumption(
            "Attacker: Network-adjacent",
            description=(
                "Positioned on the same network segment as a CI runner or developer "
                "workstation - shared cloud tenant, BGP hijack, compromised DNS resolver, "
                "or corporate proxy.  Can intercept and modify unencrypted traffic "
                "(http://, svn://) and inject HTTP redirects.  Cannot break correctly "
                "implemented TLS or SSH."
            ),
        ),
        Assumption(
            "Attacker: Compromised upstream",
            description=(
                "A dependency maintainer account taken over via phishing, credential "
                "stuffing, or MFA bypass - or a maintainer acting maliciously.  "
                "Delivers attacker-controlled content over an authenticated channel; "
                "transport security provides no protection.  Mitigated only by "
                "commit-SHA pinning and human review before accepting any update."
            ),
        ),
        Assumption(
            "Attacker: Compromised registry or CDN",
            description=(
                "Holds write access to a public package registry (PyPI) or an archive "
                "CDN node, or is BGP-adjacent to one.  Serves malicious content under "
                "a valid TLS certificate - transport integrity does not detect "
                "server-side substitution.  Only cryptographic content hashes or "
                "signed attestations provide a defence."
            ),
        ),
        Assumption(
            "Attacker: Local filesystem",
            description=(
                "Holds write access to the developer workstation or CI runner working "
                "tree - gained via a compromised dev dependency, malicious post-install "
                "hook, or lateral movement.  Can tamper with ``.dfetch_data.yaml``, "
                "patch files, and vendored source after dfetch writes them to disk."
            ),
        ),
        Assumption(
            "Attacker: Malicious manifest contributor",
            description=(
                "A repository contributor who introduces a malicious ``dfetch.yaml`` "
                "change: redirecting a dep to an attacker-controlled URL, pointing "
                "``dst:`` at a sensitive path, or embedding a credential-bearing URL.  "
                "dfetch is not the control point for this threat; code review is the "
                "intended mitigating boundary."
            ),
        ),
    ]
