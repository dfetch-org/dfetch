"""Shared building blocks for the dfetch threat models.

``tm_supply_chain.py`` and ``tm_usage.py`` both import from this module.
It provides only pure Python definitions — no pytm objects are instantiated
at module level, so it is safe to import before ``TM.reset()`` in each model.

Exports
-------
THREATS_FILE            absolute path to ``threats.json``
Control                 dataclass representing a control or known gap
build_asset_controls_index   helper to build an asset-ID → [Control] map
make_dev_env_boundary   factory — creates the shared dev-env trust boundary
make_network_boundary   factory — creates the shared Internet trust boundary
make_supply_chain_assumptions  factory — Assumptions for the SC model
make_usage_assumptions  factory — Assumptions for the runtime-usage model
"""

import os
from dataclasses import dataclass, field
from typing import Literal

from pytm import Assumption, Boundary  # noqa: pylint: disable=import-error

THREATS_FILE = os.path.join(os.path.dirname(__file__), "threats.json")


@dataclass
class Control:
    """A security control or a known gap.

    A gap is a control whose ``status`` is ``"gap"`` (or ``"planned"``).
    Both are stored in the same ``CONTROLS`` list and split at render time
    by the ``.. pytm::`` Sphinx directive.
    """

    id: str
    name: str
    description: str
    assets: list[str] = field(default_factory=list)
    threats: list[str] = field(default_factory=list)
    status: Literal["implemented", "planned", "gap"] = "implemented"
    reference: str = ""

    def to_pytm(self) -> str:
        """Return a human-readable label for traceability comments."""
        return f"[{self.id}] {self.name}"


def build_asset_controls_index(
    controls: list[Control],
) -> dict[str, list[Control]]:
    """Return an asset-ID → control list mapping built from *controls*."""
    index: dict[str, list[Control]] = {}
    for ctrl in controls:
        for asset_id in ctrl.assets:
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


def make_network_boundary() -> Boundary:
    """Create the *Internet* trust boundary."""
    b = Boundary("Internet")
    b.description = (
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
            "Harden-runner in audit mode",
            description=(
                "The ``harden-runner`` egress policy is set to ``audit``, not ``block``.  "
                "Outbound network connections from CI runners are logged but not prevented."
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
                "— it does not upgrade or reject them."
            ),
        ),
    ]
