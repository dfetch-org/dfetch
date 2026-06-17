"""Static compliance data for CRA Track B.

Contains all data classes and constants used by compliance.py.
Kept in a separate module to stay within the 1000-line limit per file.
"""

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Control:
    """An implemented security control (mirrors tm_elements.Control)."""

    id: str
    name: str
    description: str
    assets: list[str] = field(default_factory=list)
    threats: list[str] = field(default_factory=list)
    reference: str = ""


@dataclass
class ApplicableStandard:
    """One standard assessed for applicability to dfetch."""

    name: str
    reference: str
    applies: bool
    scope_note: str
    gap_note: str = ""


@dataclass
class SOImplementation:
    """Dfetch's implementation of one prEN 40000-1-4 Security Objective."""

    so_id: str
    ecr_id: str
    controls: list[str] = field(default_factory=list)
    not_applicable: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    status: Literal[
        "implemented", "partially-implemented", "planned", "not-applicable"
    ] = "partially-implemented"
    description: str = ""
    evidence_hrefs: list[tuple[str, str]] = field(default_factory=list)
    note: str = ""


@dataclass
class PartIIRequirement:
    """One CRA Annex I Part II requirement (covered by prEN 40000-1-3)."""

    id: str
    ref: str
    text: str
    controls: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    status: Literal[
        "implemented", "partially-implemented", "planned", "not-applicable"
    ] = "partially-implemented"


# ── Classification decision ───────────────────────────────────────────────────

CLASSIFICATION_DECISION: dict[str, str] = {
    "Product type": "Software tool (CLI) — Python package distributed via PyPI",
    "CRA classification": "Non-commercial open-source software (Recital 18 exemption)",
    "Legal basis": (
        "CRA Article 3(1) (scope — dfetch is not placed on the market in the context "
        "of a commercial activity); Article 3(14) (definition of open-source software "
        "steward, for reference); Recital 18 (interpretive context for the treatment "
        "of non-commercial FOSS)"
    ),
    "Mandatory obligations": "None — not a commercial product; no CE marking required",
    "Voluntary alignment": (
        "This compliance document is produced voluntarily — dfetch has no legal "
        "obligation under the CRA — to support downstream integrators who must account "
        "for open-source components in their own Article 13 conformity assessments."
    ),
}

# ── Applicable standards ──────────────────────────────────────────────────────

STANDARDS: list[ApplicableStandard] = [
    ApplicableStandard(
        name="prEN 40000-1-2",
        reference="Cyber Resilience Principles and Secure Development Lifecycle (working title; subject to change on publication)",
        applies=True,
        scope_note=(
            "Process standard covering risk-based product security across the lifecycle. "
            "The Product Security Context (§6.2) is documented in :doc:`security`. "
            "Track A threat models (`tm_supply_chain.py <https://github.com/dfetch-org/dfetch/blob/main/security/tm_supply_chain.py>`_, "
            "`tm_usage.py <https://github.com/dfetch-org/dfetch/blob/main/security/tm_usage.py>`_) implement §6.3–§6.6."
        ),
    ),
    ApplicableStandard(
        name="prEN 40000-1-3",
        reference="Vulnerability Handling Requirements",
        applies=True,
        scope_note=(
            "Covers CRA Annex I Part II vulnerability handling obligations. "
            "Addressed in the Part II table below via `SECURITY.md <https://github.com/dfetch-org/dfetch/blob/main/SECURITY.md>`_, SBOM (:ref:`C-022 <c-022>`), "
            "and dependency-review CI (:ref:`C-016 <c-016>`)."
        ),
        gap_note="No formal patch SLA or LTS backport policy defined.",
    ),
    ApplicableStandard(
        name="prEN 40000-1-4",
        reference="Generic Security Requirements (draft, indicative publication October 2027)",
        applies=True,
        scope_note=(
            "Primary standard for this document. Maps CRA Annex I Part I Art. 2(a)–(m) "
            "to Security Objectives (SO.*) and Technical Controls (GEC-*, SUM-*, etc.). "
            "The catalog is included as `security/cra_pren_4000014_oscal_catalog.json <https://github.com/dfetch-org/dfetch/blob/main/security/cra_pren_4000014_oscal_catalog.json>`_."
        ),
        gap_note="Standard is in draft; final clause numbering may change.",
    ),
    ApplicableStandard(
        name="EN 18031-1/2:2024",
        reference="Common security requirements for radio equipment (basis of prEN 40000-1-4)",
        applies=True,
        scope_note=(
            "prEN 40000-1-4 builds on EN 18031. Many technical controls (GEC-*, SUM-*, "
            "AUM-*, SSM-*, SCM-*) originate from EN 18031. dfetch's applicability is "
            "assessed at the prEN 40000-1-4 SO level."
        ),
    ),
    ApplicableStandard(
        name="ETSI EN 303 645 V3.1.3",
        reference="Cyber Security for Consumer Internet of Things",
        applies=False,
        scope_note=(
            "IoT-specific standard. dfetch is a developer CLI tool with no IoT "
            "device functionality, physical interfaces, or consumer IoT use case."
        ),
    ),
]

# ── Track B controls (C-043–C-044, C-046) ────────────────────────────────────

TRACK_B_CONTROLS: list[Control] = [
    Control(
        id="C-043",
        name="Release-gate CVE check on runtime dependencies",
        description=(
            "Run pip-audit at release time against dfetch's runtime dependencies via "
            "the OSV database; the publish workflow fails if any known vulnerability "
            "is found in the installed package set."
        ),
        threats=["Threat.KnownVulnerabilityExploitation"],
        reference=".github/workflows/python-publish.yml (Audit runtime dependencies for CVEs step)",
    ),
    Control(
        id="C-044",
        name="Data minimisation policy",
        description=(
            "Documented assertion that .dfetch_data.yaml stores only remote_url "
            "(credentials stripped — C-036), revision, optional integrity hash, and "
            "last_fetch timestamp; each field justified by functional necessity for "
            "dfetch check and dfetch freeze. No personal data processed; no telemetry."
        ),
        threats=["Threat.UnnecessaryDataMisuse"],
        reference="doc/explanation/compliance_track.rst (this document)",
    ),
    Control(
        id="C-046",
        name="Exploit mitigation inventory",
        description=(
            "Documented inventory: Python interpreter provides ASLR/DEP/stack-canaries "
            "(OS-level); no eval/exec of remote content; constant-time hash comparison "
            "(C-005); shell=False for all subprocess calls (C-007); input validation "
            "(C-008); static analysis gating (C-015, C-017). CFI/sandboxing not "
            "applicable — pure Python."
        ),
        threats=["Threat.ExploitationMitigationFailure"],
        reference="doc/explanation/compliance_track.rst (this document)",
    ),
]

# ── Track A controls (static copy — used when pytm is not available) ──────────

TRACK_A_CONTROLS: list[Control] = [
    Control(
        id="C-001",
        name="Path-traversal prevention",
        description="",
        reference="dfetch/util/util.py",
    ),
    Control(
        id="C-002",
        name="Decompression-bomb protection",
        description="",
        reference="dfetch/vcs/archive.py",
    ),
    Control(
        id="C-003",
        name="Archive symlink validation",
        description="",
        reference="dfetch/vcs/archive.py",
    ),
    Control(
        id="C-004",
        name="Archive member type checks",
        description="",
        reference="dfetch/vcs/archive.py",
    ),
    Control(
        id="C-005",
        name="Integrity hash verification",
        description="",
        reference="dfetch/vcs/integrity_hash.py",
    ),
    Control(
        id="C-006",
        name="Non-interactive VCS",
        description="",
        reference="dfetch/vcs/git.py, dfetch/vcs/svn.py",
    ),
    Control(
        id="C-007",
        name="Subprocess safety",
        description="",
        reference="dfetch/util/cmdline.py",
    ),
    Control(
        id="C-008",
        name="Manifest input validation",
        description="",
        reference="dfetch/manifest/schema.py",
    ),
    Control(
        id="C-009",
        name="Actions commit-SHA pinning",
        description="",
        reference=".github/workflows/*.yml",
    ),
    Control(
        id="C-010",
        name="OIDC trusted publishing",
        description="",
        reference=".github/workflows/python-publish.yml",
    ),
    Control(
        id="C-011",
        name="Minimal workflow permissions",
        description="",
        reference=".github/workflows/*.yml",
    ),
    Control(
        id="C-012",
        name="persist-credentials: false",
        description="",
        reference=".github/workflows/*.yml",
    ),
    Control(
        id="C-013",
        name="Harden-runner (egress block)",
        description="",
        reference=".github/workflows/*.yml",
    ),
    Control(
        id="C-015",
        name="CodeQL static analysis",
        description="",
        reference=".github/workflows/codeql-analysis.yml",
    ),
    Control(
        id="C-016",
        name="Dependency review",
        description="",
        reference=".github/workflows/dependency-review.yml",
    ),
    Control(
        id="C-017",
        name="bandit security linter",
        description="",
        reference="pyproject.toml",
    ),
    Control(id="C-021", name="Sigstore SBOM attestation", description="", reference=""),
    Control(id="C-022", name="CycloneDX SBOM on PyPI", description="", reference=""),
    Control(
        id="C-024",
        name="Explicit secret forwarding",
        description="",
        reference=".github/workflows/ci.yml",
    ),
    Control(
        id="C-026",
        name="Consumer-side package provenance verification",
        description="",
        reference="doc/howto/verify-integrity.rst",
    ),
    Control(
        id="C-032",
        name="Consumer attestation verification pins to release tag ref",
        description="",
        reference="doc/howto/verify-integrity.rst",
    ),
    Control(
        id="C-033",
        name="Ref-scoped build cache keys isolate PR and release builds",
        description="",
        reference=".github/workflows/build.yml",
    ),
    Control(
        id="C-034",
        name="Hash algorithm allowlist (SHA-256/384/512 only)",
        description="",
        reference="dfetch/vcs/integrity_hash.py",
    ),
    Control(
        id="C-036",
        name="Persisted-metadata credential redaction",
        description="",
        reference="dfetch/project/metadata.py",
    ),
    Control(
        id="C-037",
        name="SLSA Source Provenance Attestation of repository governance controls",
        description="",
        reference=".github/workflows/source-provenance.yml",
    ),
    Control(
        id="C-038",
        name="Ancestry enforcement on dfetch main branch",
        description="",
        reference=".github/workflows/",
    ),
    Control(
        id="C-039",
        name="Source build provenance and VSA attestations",
        description="",
        reference="doc/howto/verify-integrity.rst",
    ),
    Control(
        id="C-040",
        name="Test result attestation on source archive",
        description="",
        reference=".github/workflows/test.yml",
    ),
    Control(
        id="C-041",
        name="Winget manifest PRs reviewed by community maintainers",
        description="",
        reference=".github/workflows/winget-publish.yml",
    ),
    Control(
        id="C-042",
        name="WINGET_TOKEN scoped to dedicated Winget environment",
        description="",
        reference=".github/workflows/winget-publish.yml",
    ),
    Control(
        id="C-045",
        name="Plaintext transport detection",
        description="",
        reference="dfetch/manifest/project.py, dfetch/project/subproject.py",
    ),
]

# ── Annex V technical documentation map ──────────────────────────────────────

ANNEX_V_MAP: list[tuple[str, str]] = [
    (
        "**1. General description** — intended purpose, product name and version, "
        "manufacturer address",
        ":doc:`security` § *Product and manufacturer identification*; "
        ":doc:`../reference/manifest` (manifest schema and version field)",
    ),
    (
        "**2. Design and development** — software architecture; how components "
        "build on or feed into each other",
        ":doc:`../explanation/architecture` (layer diagram and module overview); "
        ":doc:`security_pipeline` § *Threat model pipeline* (security-relevant "
        "component relationships)",
    ),
    (
        "**3. Production and monitoring** — build pipeline, dependency management, "
        "CI/CD monitoring",
        ":doc:`security_pipeline` § *Compliance pipeline* and *Release attestations*; "
        "CI workflows in "
        "`\\.github/workflows/ <https://github.com/dfetch-org/dfetch/tree/main/.github/workflows>`_",
    ),
    (
        "**4. Cybersecurity risk assessment** (Article 13(2)) — asset identification, "
        "threat analysis, risk treatment",
        ":doc:`threat_model_supply_chain` (pre-install lifecycle); "
        ":doc:`threat_model_usage` (runtime invocation); "
        "see also :doc:`security` § *Risk Rating Methodology*",
    ),
    (
        "**5. Implemented security solutions and applied standards** — "
        "list of harmonised standards applied; where not applied, description of how "
        "each Annex I requirement is met",
        "This page (§§ *Applicable Standards*, *Part I*, *Part II*); "
        ":doc:`control_register` (all 46 controls with references); "
        "OSCAL Component Definition "
        "`security/dfetch.component-definition.json "
        "<https://github.com/dfetch-org/dfetch/blob/main/security/dfetch.component-definition.json>`_",
    ),
    (
        "**6. EU Declaration of Conformity** (Annex IV)",
        "Not required. dfetch is outside mandatory CRA scope (see "
        "*Classification Decision* above). No CE marking is affixed.",
    ),
]

# ── Security Objective implementations ───────────────────────────────────────

SO_IMPLEMENTATIONS: list[SOImplementation] = [
    # ECR-a: Vulnerability Assessment
    SOImplementation(
        so_id="so-vulnerability-management-process",
        ecr_id="ecr-a",
        controls=["C-015", "C-016", "C-017", "C-022", "C-040", "C-043"],
        status="implemented",
        description=(
            "GEC-1: C-015 (CodeQL), C-016 (dependency-review), C-017 (bandit), "
            "C-022 (SBOM) address known-vulnerability detection in CI. "
            "C-043 (pip-audit OSV gate) blocks release if runtime dependencies "
            "carry known vulnerabilities."
        ),
        evidence_hrefs=[
            (".github/workflows/codeql-analysis.yml", "C-015 CodeQL static analysis"),
            (".github/workflows/dependency-review.yml", "C-016 Dependency review"),
            (
                ".github/workflows/python-publish.yml",
                "C-022 SBOM generation; C-043 pip-audit CVE gate",
            ),
        ],
    ),
    # ECR-b: Secure Configuration
    SOImplementation(
        so_id="so-secure-default-configuration",
        ecr_id="ecr-b",
        controls=["C-001", "C-002"],
        not_applicable=[
            "GEC-2, GEC-3, GEC-4, GEC-5 (no exposed network services — CLI tool)",
            "GEC-7 (no external sensing capabilities)",
            "AUM-5 (no password or authentication mechanism)",
        ],
        gaps=[
            "Integrity hash verification (:ref:`C-005 <c-005>`) is opt-in; manifest entries without an ``integrity`` field are fetched without hash verification by default"
        ],
        status="partially-implemented",
        description=(
            "GEC-12 (no unneeded software components): C-001 enforces minimal "
            "runtime dependencies. dfetch does not expose network services."
        ),
        evidence_hrefs=[
            ("dfetch/util/util.py", "C-001 Path-traversal prevention"),
            (
                "dfetch/vcs/archive.py",
                "C-002 Decompression-bomb protection; C-003 Symlink validation; C-004 Member-type checks",
            ),
        ],
    ),
    SOImplementation(
        so_id="so-secure-startup-config",
        ecr_id="ecr-b",
        not_applicable=[
            "GEC-9 (no security-relevant startup configuration state in dfetch)"
        ],
        status="not-applicable",
        description="dfetch reads only its manifest at startup; no security-sensitive config initialisation.",
    ),
    SOImplementation(
        so_id="so-factory-reset",
        ecr_id="ecr-b",
        not_applicable=[
            "DLM-1-b, GEC-10 (no persistent device state requiring factory reset — CLI tool)"
        ],
        status="not-applicable",
        description="dfetch is a stateless CLI tool; no factory-reset concept applies.",
    ),
    # ECR-c: Security Updates
    SOImplementation(
        so_id="so-updateability",
        ecr_id="ecr-c",
        not_applicable=[
            "No dfetch-specific control required — updateability is inherent to "
            "pip distribution (``pip install --upgrade dfetch``) and GitHub Releases. "
            "SUM-1/SUM-2 are satisfied by the distribution mechanism, not by a "
            "runtime dfetch feature."
        ],
        status="implemented",
        description=(
            "SUM-1/SUM-2: Updates distributed via PyPI (``pip install --upgrade dfetch``) "
            "and GitHub Releases. pip's TLS-protected download and version-pinning "
            "model satisfies SUM-2. No dfetch-specific update mechanism is needed or "
            "implemented; the package manager is the update vehicle."
        ),
        note=(
            "**ECR-C SO.Updateability** — SUM-1/SUM-2 require the manufacturer to make "
            "security updates available through a secure channel. dfetch publishes every "
            "release to PyPI (TLS-protected, OIDC-authenticated via :ref:`C-010 <c-010>`) "
            "and GitHub Releases (with release attestations per :ref:`C-039 <c-039>`). "
            "The CVE gate (:ref:`C-043 <c-043>`) blocks release if known vulnerabilities "
            "are present in runtime dependencies. Providing the update *mechanism* is the "
            "manufacturer's obligation under SUM-1/SUM-2; delivery to the end user is the "
            "responsibility of the user's package manager."
        ),
    ),
    SOImplementation(
        so_id="so-automatic-updates",
        ecr_id="ecr-c",
        not_applicable=[
            "SUM-3 (automatic updates managed by pip/pipenv/poetry — not dfetch itself)"
        ],
        status="not-applicable",
        description="Update automation is the responsibility of the user's package manager.",
    ),
    SOImplementation(
        so_id="so-user-update-notification",
        ecr_id="ecr-c",
        controls=[],
        status="implemented",
        description=(
            "UNM-4: ``dfetch check`` and ``dfetch environment`` both call "
            "``newer_version_available()`` (``dfetch/util/github_version_check.py``), "
            "which polls the GitHub releases API and prints a notice if a newer dfetch "
            "release exists."
        ),
        evidence_hrefs=[
            (
                "dfetch/util/github_version_check.py",
                "Version availability check implementation",
            ),
            (
                "dfetch/commands/check.py",
                "Version check in dfetch check (suppressed in CI)",
            ),
            ("dfetch/commands/environment.py", "Version check in dfetch environment"),
        ],
        note=(
            "**ECR-C SO.UserUpdateNotification** — ``dfetch check`` and ``dfetch environment`` "
            "both call ``newer_version_available()`` (``dfetch/util/github_version_check.py``), "
            "which polls the GitHub releases API and prints a notice if a newer dfetch release "
            "exists. ``dfetch check`` suppresses the call when the ``CI`` environment variable "
            'is set (``check.py`` line 102: ``if not os.environ.get("CI")``); '
            "``dfetch environment`` does not apply this guard and always performs the check."
        ),
    ),
    SOImplementation(
        so_id="so-postpone-updates",
        ecr_id="ecr-c",
        not_applicable=[
            "SUM-4 (update scheduling controlled by pip/pipenv — not dfetch)"
        ],
        status="not-applicable",
        description="Postponement is handled by the user's package manager.",
    ),
    # ECR-d: Access Control
    SOImplementation(
        so_id="so-access-control",
        ecr_id="ecr-d",
        controls=["C-006", "C-036"],
        not_applicable=[
            "ACM-2, AUM-2, AUM-3, AUM-4, AUM-6 "
            "(dfetch has no user-facing authentication or access control)"
        ],
        gaps=[
            "dfetch has no native authentication or authorisation layer; access control is "
            "fully delegated to the underlying VCS server and host OS. C-006 prevents "
            "interactive credential prompts, and C-036 strips credentials from persisted "
            "metadata — both are confidentiality controls, not access-control mechanisms "
            "in the authentication/authorisation sense"
        ],
        status="partially-implemented",
        description=(
            "dfetch delegates authentication to the host VCS client (git, svn) and "
            "the OS credential store. C-006 prevents SSH command injection; "
            "C-036 strips credentials from stored metadata."
        ),
        evidence_hrefs=[
            ("dfetch/vcs/git.py", "C-006 Non-interactive git (prevents SSH injection)"),
            ("dfetch/vcs/svn.py", "C-006 Non-interactive svn"),
            (
                "dfetch/project/metadata.py",
                "C-036 Credential redaction from stored metadata",
            ),
        ],
    ),
    SOImplementation(
        so_id="so-access-control-report",
        ecr_id="ecr-d",
        controls=["C-045"],
        gaps=["No persistent log of unauthorised access attempts"],
        status="partially-implemented",
        description=(
            "GEC-13: C-045 (plaintext transport warning) alerts on unauthenticated "
            "connections. No persistent security event log."
        ),
        evidence_hrefs=[
            ("dfetch/manifest/project.py", "C-045 Plaintext transport detection"),
            ("dfetch/project/subproject.py", "C-045 Plaintext transport warning"),
        ],
    ),
    # ECR-e: Confidentiality
    SOImplementation(
        so_id="so-data-stored-confidentiality",
        ecr_id="ecr-e",
        controls=["C-036"],
        status="implemented",
        description=(
            "SSM-1/SSM-3: The developer workstation is a trusted boundary (as established "
            "in the usage threat model: 'Trusted at workstation invocation time'). "
            "C-036 strips all credentials from .dfetch_data.yaml before write, so the "
            "stored file contains only non-sensitive metadata (remote URL without userinfo, "
            "revision, content hash, timestamp). The threat model explicitly marks "
            "metadata_store.storesSensitiveData = False and isDestEncryptedAtRest = False "
            "as a conscious design choice; no encryption-at-rest is required."
        ),
        evidence_hrefs=[
            ("dfetch/project/metadata.py", "C-036 Credential redaction before write"),
        ],
    ),
    SOImplementation(
        so_id="so-data-processed-confidentiality",
        ecr_id="ecr-e",
        controls=["C-005", "C-034"],
        status="implemented",
        description=(
            "GEC-8: C-005 (constant-time comparison), C-034 (temp-file cleanup) "
            "protect in-process data."
        ),
        evidence_hrefs=[
            (
                "dfetch/vcs/integrity_hash.py",
                "C-005 Constant-time HMAC comparison; C-034 SHA-256/384/512 allowlist",
            ),
        ],
    ),
    SOImplementation(
        so_id="so-data-transmitted-confidentiality",
        ecr_id="ecr-e",
        controls=["C-045"],
        gaps=[
            "C-045 warns on plaintext-scheme URLs but does not refuse to proceed; "
            "TLS/SSH confidentiality is provided by the underlying VCS client, not "
            "enforced by dfetch itself"
        ],
        status="partially-implemented",
        description=(
            "SCM-3/SCM-4: Plaintext transport (http://, git://, svn://) is accepted "
            "by design for legacy source compatibility. C-045 detects and warns the "
            "user before proceeding — 'Detection only; dfetch still proceeds with the "
            "plaintext connection; the control raises user awareness but does not "
            "enforce scheme selection' (usage threat model, C-045 description). "
            "For archive URLs over HTTP, C-005 (integrity hash) verifies that content "
            "has not been tampered with in transit; it does not encrypt or conceal the "
            "content. This is a deliberate design decision, not a residual gap."
        ),
        evidence_hrefs=[
            ("dfetch/manifest/project.py", "C-045 Plaintext transport detection"),
            ("dfetch/vcs/integrity_hash.py", "C-005 Archive content integrity hash"),
        ],
    ),
    SOImplementation(
        so_id="so-com-auth-e",
        ecr_id="ecr-e",
        controls=["C-045"],
        gaps=[
            "Server authentication (TLS certificate verification, SSH host-key checking) "
            "is delegated to the OS trust store and VCS client; dfetch does not "
            "independently authenticate remote endpoints and cannot enforce authenticated "
            "channels when C-045's warning is overridden by the user"
        ],
        status="partially-implemented",
        description=(
            "SCM-2: HTTPS connections authenticate via TLS CA chain (C-003); SSH "
            "connections authenticate via host-key verification (C-004). Plain git:// "
            "and svn:// connections lack channel-level authentication but are accepted "
            "by design for legacy compatibility — the same rationale as "
            "DataTransmittedConfidentiality — and C-045 warns the user. The usage "
            "threat model notes the network adversary 'cannot break correctly "
            "implemented TLS or SSH'; the residual risk for unauthenticated transports "
            "is an accepted design trade-off."
        ),
        evidence_hrefs=[
            (
                "dfetch/vcs/archive.py",
                "C-003 Archive symlink validation; C-004 Archive member-type checks",
            ),
            ("dfetch/manifest/project.py", "C-045 Plaintext transport detection"),
        ],
    ),
    SOImplementation(
        so_id="so-secure-provisioning",
        ecr_id="ecr-e",
        controls=["C-005"],
        not_applicable=["CCK-1, CCK-2, CCK-3 (dfetch manages no cryptographic keys)"],
        status="partially-implemented",
        description=(
            "CRY-1: C-005 uses Python's hashlib with SHA-256 for integrity hashes. "
            "No key management is required or performed by dfetch."
        ),
        evidence_hrefs=[
            ("dfetch/vcs/integrity_hash.py", "C-005 SHA-256 integrity hash (hashlib)"),
        ],
    ),
    # ECR-f: Integrity
    SOImplementation(
        so_id="so-data-stored-integrity",
        ecr_id="ecr-f",
        controls=["C-005"],
        gaps=["Integrity hash opt-in only; not enforced by default for git/svn"],
        status="partially-implemented",
        description=(
            "SSM-2: C-005 (integrity hash in .dfetch_data.yaml) provides optional "
            "stored-data integrity verification."
        ),
        evidence_hrefs=[
            (
                "dfetch/vcs/integrity_hash.py",
                "C-005 Integrity hash stored in .dfetch_data.yaml",
            ),
        ],
    ),
    SOImplementation(
        so_id="so-data-processed-integrity",
        ecr_id="ecr-f",
        controls=["C-005", "C-034"],
        status="implemented",
        description="GEC-8: C-005 and C-034 protect data integrity during processing.",
        evidence_hrefs=[
            (
                "dfetch/vcs/integrity_hash.py",
                "C-005 Integrity hash; C-034 SHA-256/384/512 allowlist",
            ),
        ],
    ),
    SOImplementation(
        so_id="so-data-transmitted-integrity",
        ecr_id="ecr-f",
        controls=["C-005"],
        gaps=[
            "C-005 provides end-to-end hash verification for archive sources only (opt-in); "
            "git and svn sources rely solely on VCS object integrity (SHA-1/SHA-256 object "
            "model) and TLS/SSH channel integrity — no dfetch-level hash verification"
        ],
        status="partially-implemented",
        description=(
            "SCM-2: TLS (C-003) and SSH (C-004) provide channel-level integrity. "
            "Commit-hash pinning (rev: <sha>) provides content-level integrity for git."
        ),
        evidence_hrefs=[
            (
                "dfetch/vcs/archive.py",
                "C-003 Archive symlink validation; C-004 Archive member-type checks",
            ),
        ],
    ),
    SOImplementation(
        so_id="so-integrity-report",
        ecr_id="ecr-f",
        controls=["C-045"],
        gaps=["No persistent integrity-violation log"],
        status="partially-implemented",
        description=(
            "GEC-13-f: dfetch surfaces transport-integrity warnings (C-045) at runtime "
            "but does not maintain a persistent security event log."
        ),
        evidence_hrefs=[
            (
                "dfetch/manifest/project.py",
                "C-045 Plaintext transport warning at runtime",
            ),
        ],
    ),
    # ECR-g: Data Minimisation
    SOImplementation(
        so_id="so-data-minimization",
        ecr_id="ecr-g",
        controls=["C-044"],
        not_applicable=[
            "UNM-1, UNM-2 (dfetch processes no personal data requiring user notification)",
            "DTM-3 (no optional data processing to configure)",
        ],
        status="implemented",
        description=(
            "DTM-1: C-044 documents that .dfetch_data.yaml is limited to "
            "remote_url (stripped), revision, optional hash, and last_fetch — each "
            "justified by functional necessity. "
            "DTM-2: met by design — dfetch collects no telemetry or optional data."
        ),
        evidence_hrefs=[
            (
                "dfetch/project/metadata.py",
                "Metadata model — only non-sensitive fields stored",
            ),
        ],
    ),
    # ECR-h: Availability
    SOImplementation(
        so_id="so-incident-recovery",
        ecr_id="ecr-h",
        not_applicable=[
            "RLM-2, RLM-6 (CLI tool; no persistent device state or control-system backup needed)"
        ],
        status="not-applicable",
        description=(
            "dfetch is a stateless CLI tool. Recovery consists of re-running "
            "dfetch update, which re-fetches all dependencies."
        ),
    ),
    SOImplementation(
        so_id="so-incident-resilience",
        ecr_id="ecr-h",
        controls=["C-002", "C-007"],
        not_applicable=[
            "RLM-3, RLM-4, RLM-5 (no persistent network services to prioritize)"
        ],
        gaps=["No timeout on VCS operations (potential resource exhaustion)"],
        status="partially-implemented",
        description=(
            "RLM-1: C-002 (no background daemon) and C-007 (subprocess controls) "
            "reduce exposure. DoS resilience applies only to the transient fetch operation."
        ),
    ),
    # ECR-i: Minimize Negative Impact
    SOImplementation(
        so_id="so-limit-external-impact",
        ecr_id="ecr-i",
        controls=["C-001", "C-007"],
        not_applicable=[
            "TCM-1 (dfetch makes targeted VCS fetch requests; "
            "no ambient outbound traffic to throttle)"
        ],
        gaps=[
            "Archive HTTP operations time out at 15 s (reachability) and 60 s (download) "
            "via ``archive.py``; git and svn subprocess calls have no timeout and can "
            "stall indefinitely"
        ],
        status="partially-implemented",
        description=(
            "GEC-8-i: C-001 (minimal deps) and C-007 (subprocess controls) reduce "
            "the risk of dfetch being weaponised against external services. "
            "LIM-1: dfetch fetches only what is listed in the manifest."
        ),
        evidence_hrefs=[
            ("dfetch/util/util.py", "C-001 Path-traversal and dependency minimisation"),
            ("dfetch/util/cmdline.py", "C-007 Subprocess safety (shell=False)"),
        ],
    ),
    SOImplementation(
        so_id="so-prevent-attack-propagation",
        ecr_id="ecr-i",
        controls=["C-001", "C-008"],
        status="implemented",
        description=(
            "LIM-2: Path traversal to destinations outside the project tree is "
            "prevented by C-001 (check_no_path_traversal() via realpath). "
            "The residual risk of a manifest declaring a legitimate but sensitive "
            "dst: (e.g. .github/workflows/) is accepted in the usage threat model "
            "under the 'Manifest under code review' assumption: dfetch.yaml is "
            "version-controlled and any such dst: change would be rejected at review."
        ),
        evidence_hrefs=[
            ("dfetch/util/util.py", "C-001 check_no_path_traversal() via realpath"),
            ("dfetch/manifest/schema.py", "C-008 Manifest URL and path validation"),
        ],
    ),
    SOImplementation(
        so_id="so-monitor-external-impact",
        ecr_id="ecr-i",
        not_applicable=[
            "NMM-1 (dfetch makes no ambient outbound network traffic to monitor)"
        ],
        status="not-applicable",
        description="dfetch makes targeted, user-initiated VCS requests only.",
    ),
    # ECR-j: Attack Surface Minimization
    SOImplementation(
        so_id="so-reduce-attack-surface",
        ecr_id="ecr-j",
        controls=["C-001", "C-003", "C-004", "C-007", "C-008"],
        not_applicable=[
            "GEC-2-j, GEC-3-j, GEC-4-j, GEC-5-j, GEC-7-j "
            "(dfetch exposes no network services)"
        ],
        gaps=[
            "No domain or URL-scheme allowlist constrains which remote URLs the manifest "
            "may reference; git and svn subprocess calls have no timeout (archive HTTP "
            "operations time out at 15 s / 60 s)"
        ],
        status="partially-implemented",
        description=(
            "GEC-6: C-007 (no shell=True), C-008 (URL/path validation) implement "
            "input validation. GEC-12-j: C-001 enforces minimal runtime dependencies."
        ),
        evidence_hrefs=[
            (
                "dfetch/util/cmdline.py",
                "C-007 Subprocess safety (shell=False everywhere)",
            ),
            ("dfetch/manifest/schema.py", "C-008 Manifest input validation"),
            ("dfetch/util/util.py", "C-001 Minimal dependency footprint"),
            (
                "dfetch/vcs/archive.py",
                "C-003 Symlink validation; C-004 Member-type checks",
            ),
        ],
    ),
    # ECR-k: Exploit Mitigation
    SOImplementation(
        so_id="so-reduce-impact-of-incident",
        ecr_id="ecr-k",
        controls=["C-005", "C-007", "C-015", "C-017", "C-046"],
        not_applicable=[
            "Compile-time mitigations (CFI, sandboxing) — not applicable to pure Python"
        ],
        status="implemented",
        description=(
            "GEC-11: Python interpreter provides ASLR/DEP/stack-canaries (OS-level). "
            "dfetch: no eval/exec of remote content; constant-time comparison (C-005); "
            "shell=False (C-007); static analysis (C-015, C-017). "
            "C-046 formalises this inventory in doc/explanation/compliance_track.rst."
        ),
        evidence_hrefs=[
            (".github/workflows/codeql-analysis.yml", "C-015 CodeQL static analysis"),
            ("pyproject.toml", "C-017 bandit security linter configuration"),
            ("dfetch/vcs/integrity_hash.py", "C-005 Constant-time HMAC comparison"),
            ("dfetch/util/cmdline.py", "C-007 No shell=True in subprocess calls"),
        ],
    ),
    # ECR-l: Monitoring and Logging
    SOImplementation(
        so_id="so-log-security-relevant-activities",
        ecr_id="ecr-l",
        controls=[],
        gaps=[
            "No persistent structured security event log (LGM-1/2/3/4 gap). dfetch prints "
            "operational output to stderr but does not retain it, does not record which "
            "credentials were used, which files were modified, or when remote access occurred. "
            "C-036 ensures credentials are excluded from operational output but is not a "
            "logging control"
        ],
        status="partially-implemented",
        description=(
            "LGM-1: dfetch logs warnings to stderr during a run but does not persist "
            "them. LGM-6: C-036 ensures credentials are not logged."
        ),
        evidence_hrefs=[
            (
                "dfetch/project/metadata.py",
                "C-036 Credential exclusion from stored metadata and logs",
            ),
            ("dfetch/log/", "Logging module — transient stderr only"),
        ],
    ),
    SOImplementation(
        so_id="so-monitor-security-relevant-activities",
        ecr_id="ecr-l",
        controls=["C-045"],
        not_applicable=["NMM-1 (no ambient network monitoring)"],
        status="partially-implemented",
        description=(
            "MON-1: C-045 (plaintext transport detection) monitors for insecure "
            "connections at runtime and surfaces warnings to the user."
        ),
        evidence_hrefs=[
            ("dfetch/manifest/project.py", "C-045 Plaintext transport detection"),
            ("dfetch/project/subproject.py", "C-045 Runtime transport monitoring"),
        ],
    ),
    SOImplementation(
        so_id="so-option-disable-data-logging",
        ecr_id="ecr-l",
        not_applicable=["LGM-5 (dfetch does not persist logs; nothing to disable)"],
        status="not-applicable",
        description="dfetch emits transient stderr warnings only; no persistent log to opt out of.",
    ),
    SOImplementation(
        so_id="so-option-disable-data-monitoring",
        ecr_id="ecr-l",
        not_applicable=["MON-2 (no persistent monitoring to disable)"],
        status="not-applicable",
        description="dfetch performs no ongoing monitoring between invocations.",
    ),
    # ECR-m: Data Deletion
    SOImplementation(
        so_id="so-secure-data-deletion",
        ecr_id="ecr-m",
        not_applicable=[
            "No dfetch-specific secure-deletion control is required: dfetch stores "
            "no personal data and no keying material. The only on-disk state is "
            ".dfetch_data.yaml (non-sensitive metadata) and vendored source files "
            "(third-party code, not user data). Standard OS file deletion (rm / del) "
            "is sufficient; cryptographic wipe is not warranted. DLM-1 is satisfied "
            "by design (no sensitive data to wipe), not by a dedicated dfetch control."
        ],
        status="implemented",
        description=(
            "DLM-1: .dfetch_data.yaml contains only non-sensitive metadata — "
            "remote URL (credentials stripped by C-036), revision, optional content "
            "hash, and last-fetch timestamp. Standard OS file deletion is sufficient; "
            "no secure-wipe is required. Users delete the file and vendored directories "
            "to remove all dfetch data. ECR-m is satisfied by design because dfetch "
            "collects no personal data, credentials, or keying material on disk."
        ),
        note=(
            "**ECR-M SO.SecureDataDeletion** — No dfetch-specific control is needed. "
            "DLM-1 is satisfied by design: dfetch stores no personal data, credentials, "
            "or cryptographic keying material on disk. The only on-disk state is "
            "``.dfetch_data.yaml`` (non-sensitive dependency metadata — credentials "
            "stripped by :ref:`C-036 <c-036>`) and vendored source files (third-party "
            "code). Standard OS file deletion (``rm`` / ``del``) is sufficient to remove "
            "all dfetch data; no secure-wipe facility is warranted."
        ),
    ),
    SOImplementation(
        so_id="so-data-transmitted-confidentiality-m",
        ecr_id="ecr-m",
        not_applicable=[
            "DLM-2, DLM-3, DLM-4 (dfetch does not export user data to external systems)"
        ],
        status="not-applicable",
        description="dfetch does not provide data export or transfer functionality.",
    ),
    SOImplementation(
        so_id="so-data-transmitted-integrity-m",
        ecr_id="ecr-m",
        not_applicable=["DLM-3 (no data export)"],
        status="not-applicable",
        description="Not applicable — see SO.DataTransmittedConfidentiality (data export context).",
    ),
    SOImplementation(
        so_id="so-com-auth-m",
        ecr_id="ecr-m",
        not_applicable=["DLM-4 (no data export)"],
        status="not-applicable",
        description="Not applicable — see SO.DataTransmittedConfidentiality (data export context).",
    ),
]

# ── CRA Part II requirements (prEN 40000-1-3) ────────────────────────────────

PART_II_REQUIREMENTS: list[PartIIRequirement] = [
    PartIIRequirement(
        id="pii-01",
        ref="Part II §1",
        text="Identify and document vulnerabilities and components (SBOM).",
        controls=["C-021", "C-022"],
        status="implemented",
    ),
    PartIIRequirement(
        id="pii-02",
        ref="Part II §2",
        text="Address vulnerabilities without delay; provide free security updates.",
        controls=["C-015", "C-016", "SECURITY.md"],
        gaps=[
            "No LTS backport policy (latest release only — documented in SECURITY.md)"
        ],
        status="partially-implemented",
    ),
    PartIIRequirement(
        id="pii-03",
        ref="Part II §3",
        text="Apply effective coordinated vulnerability disclosure (CVD) policy.",
        controls=["SECURITY.md"],
        status="implemented",
    ),
    PartIIRequirement(
        id="pii-04",
        ref="Part II §4",
        text="Report actively exploited vulnerabilities to national CSIRT and ENISA.",
        status="not-applicable",
    ),
    PartIIRequirement(
        id="pii-05",
        ref="Part II §5",
        text="Publish coordinated vulnerability disclosure policy.",
        controls=["SECURITY.md"],
        status="implemented",
    ),
    PartIIRequirement(
        id="pii-06",
        ref="Part II §6",
        text="Share information on vulnerabilities in integrated components.",
        controls=["C-022", "C-016"],
        gaps=["No proactive downstream notification process"],
        status="partially-implemented",
    ),
    PartIIRequirement(
        id="pii-07",
        ref="Part II §7",
        text="Provide security updates free of charge for the support period.",
        controls=["MIT licence", "PyPI", "SECURITY.md"],
        status="implemented",
    ),
]
