"""Model-building blocks for the dfetch threat models.

Provides data classes, trust boundary factories, and assumption factories used
by both the supply-chain and usage threat models.  No pytm objects at module
level, so it is safe to import before ``TM.reset()``.
"""

import os
from dataclasses import dataclass, field
from typing import Literal

from pytm import Assumption, Boundary

from security.tm_controls_data import Control  # noqa: F401  # re-exported

THREATS_FILE = os.path.join(os.path.dirname(__file__), "threats.json")


@dataclass
class ThreatResponse:
    """Per-threat handling decision: how this model responds to a specific threat.

    ``target`` names the single canonical element or dataflow the threat is
    documented against.  pytm matches a threat to every element its condition
    satisfies, so a threat that applies to many elements yields many identical
    findings; the rendered report collapses these to one row and shows this
    target.  Leave empty for threats that match a single element.
    """

    threat_id: str
    status: Literal["avoid", "mitigate", "accept", "transfer"]
    risk: Literal["Critical", "High", "Medium", "Low"] = "Medium"
    stride: list[str] = field(default_factory=list)
    note: str = ""
    target: str = ""


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
