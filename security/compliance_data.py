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
    "Legal basis": "Article 3(14), Recital 18, Article 13(5) of Regulation (EU) 2024/2847",
    "Mandatory obligations": "None — not a commercial product; no CE marking required",
    "Voluntary alignment": (
        "This Track B document is produced voluntarily under Article 13(5) to support "
        "downstream integrators who must account for open-source components in their "
        "own CRA conformity assessments."
    ),
}

# ── Applicable standards ──────────────────────────────────────────────────────

STANDARDS: list[ApplicableStandard] = [
    ApplicableStandard(
        name="prEN 40000-1-2",
        reference="Cyber Resilience Principles and Risk Management",
        applies=True,
        scope_note=(
            "Process standard covering risk-based product security across the lifecycle. "
            "The Product Security Context (§6.2) is documented in security.rst. "
            "Track A threat models (tm_supply_chain.py, tm_usage.py) implement §6.3–§6.6."
        ),
    ),
    ApplicableStandard(
        name="prEN 40000-1-3",
        reference="Vulnerability Handling Requirements",
        applies=True,
        scope_note=(
            "Covers CRA Annex I Part II vulnerability handling obligations. "
            "Addressed in the Part II table below via SECURITY.md, SBOM (C-022), "
            "and dependency-review CI (C-016)."
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
            "The catalog is included as security/cra_pren_4000014_oscal_catalog.json."
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

# ── Track B controls (C-043–C-046) ───────────────────────────────────────────

TRACK_B_CONTROLS: list[Control] = [
    Control(
        id="C-043",
        name="Release-gate CVE check on runtime dependencies",
        description=(
            "Run pip-audit or osv-scanner at release time against dfetch's runtime "
            "dependencies; fail the publish workflow if any Critical/High CVE is "
            "unresolved."
        ),
        threats=["Threat.KnownVulnerabilityExploitation"],
        reference=".github/workflows/python-publish.yml (planned CI addition)",
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
        id="C-045",
        name="Destination path sensitivity warning",
        description=(
            "Non-blocking warning when dst: resolves to a security-sensitive path "
            "(.github/workflows, .gitlab-ci.yml, CI/CD directories), following the "
            "plaintext_warning() pattern."
        ),
        threats=["Threat.ExtServiceAvailabilityDegradation"],
        reference="dfetch/project/subproject.py (planned: _is_sensitive_dst())",
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

# ── Security Objective implementations ───────────────────────────────────────

SO_IMPLEMENTATIONS: list[SOImplementation] = [
    # ECR-a: Vulnerability Assessment
    SOImplementation(
        so_id="so-vulnerability-management-process",
        ecr_id="ecr-a",
        controls=["C-015", "C-016", "C-017", "C-022"],
        gaps=["No CVE gate at release time (→ C-043 planned)"],
        status="partially-implemented",
        description=(
            "GEC-1: C-015 (CodeQL), C-016 (dependency-review), C-017 (bandit), "
            "C-022 (SBOM) address known-vulnerability detection in CI."
        ),
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
        status="partially-implemented",
        description=(
            "GEC-12 (no unneeded software components): C-001 enforces minimal "
            "runtime dependencies. dfetch does not expose network services."
        ),
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
        status="implemented",
        description=(
            "SUM-1/SUM-2: Updates distributed via PyPI (pip install --upgrade dfetch) "
            "and GitHub Releases. pip's TLS-protected download satisfies SUM-2."
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
        controls=["C-040"],
        status="implemented",
        description=(
            "UNM-4: dfetch check and dfetch environment report when a newer dfetch "
            "version is available (C-040)."
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
        status="partially-implemented",
        description=(
            "dfetch delegates authentication to the host VCS client (git, svn) and "
            "the OS credential store. C-006 prevents SSH command injection; "
            "C-036 strips credentials from stored metadata."
        ),
    ),
    SOImplementation(
        so_id="so-access-control-report",
        ecr_id="ecr-d",
        controls=["C-009"],
        gaps=["No persistent log of unauthorised access attempts"],
        status="partially-implemented",
        description=(
            "GEC-13: C-009 (plaintext transport warning) alerts on unauthenticated "
            "connections. No persistent security event log."
        ),
    ),
    # ECR-e: Confidentiality
    SOImplementation(
        so_id="so-data-stored-confidentiality",
        ecr_id="ecr-e",
        controls=["C-036"],
        gaps=[".dfetch_data.yaml stored as plaintext YAML (no encryption at rest)"],
        status="partially-implemented",
        description=(
            "SSM-1/SSM-3: C-036 strips userinfo from URLs before storage. The "
            ".dfetch_data.yaml file itself is not encrypted; encryption would require "
            "key management infrastructure not appropriate for a developer tool."
        ),
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
    ),
    SOImplementation(
        so_id="so-data-transmitted-confidentiality",
        ecr_id="ecr-e",
        controls=["C-009"],
        gaps=[
            "HTTP accepted for remote URLs (SCM-3/SCM-4 gap; mitigated by C-009 warning)"
        ],
        status="partially-implemented",
        description=(
            "SCM-3/SCM-4: dfetch warns on plaintext transport (C-009) but accepts "
            "HTTP remote URLs to avoid breaking existing manifests."
        ),
    ),
    SOImplementation(
        so_id="so-com-auth-e",
        ecr_id="ecr-e",
        controls=["C-003", "C-004"],
        gaps=["No end-to-end authenticity verification for plain git/svn transport"],
        status="partially-implemented",
        description=(
            "SCM-2: C-003 (TLS CA verification for HTTPS) and C-004 (SSH host-key "
            "checking) provide authenticity for most connections."
        ),
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
    ),
    SOImplementation(
        so_id="so-data-processed-integrity",
        ecr_id="ecr-f",
        controls=["C-005", "C-034"],
        status="implemented",
        description="GEC-8: C-005 and C-034 protect data integrity during processing.",
    ),
    SOImplementation(
        so_id="so-data-transmitted-integrity",
        ecr_id="ecr-f",
        controls=["C-003", "C-004"],
        gaps=[
            "No end-to-end hash for git/svn transport beyond TLS/SSH channel integrity"
        ],
        status="partially-implemented",
        description=(
            "SCM-2: TLS (C-003) and SSH (C-004) provide channel-level integrity. "
            "Commit-hash pinning (rev: <sha>) provides content-level integrity for git."
        ),
    ),
    SOImplementation(
        so_id="so-integrity-report",
        ecr_id="ecr-f",
        controls=["C-009"],
        gaps=["No persistent integrity-violation log"],
        status="partially-implemented",
        description=(
            "GEC-13-f: dfetch surfaces transport-integrity warnings (C-009) at runtime "
            "but does not maintain a persistent security event log."
        ),
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
        status="planned",
        description=(
            "DTM-1: C-044 (planned) documents that .dfetch_data.yaml is limited to "
            "remote_url (stripped), revision, optional hash, and last_fetch — each "
            "justified by functional necessity. "
            "DTM-2: met by design — dfetch collects no telemetry or optional data."
        ),
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
        status="partially-implemented",
        description=(
            "GEC-8-i: C-001 (minimal deps) and C-007 (subprocess controls) reduce "
            "the risk of dfetch being weaponised against external services. "
            "LIM-1: dfetch fetches only what is listed in the manifest."
        ),
    ),
    SOImplementation(
        so_id="so-prevent-attack-propagation",
        ecr_id="ecr-i",
        controls=["C-045"],
        gaps=[
            "No warning when dst: targets security-sensitive paths (→ C-045 planned)"
        ],
        status="planned",
        description=(
            "LIM-2: C-045 (planned) warns when dst: resolves to paths such as "
            ".github/workflows or .gitlab-ci.yml that could propagate a supply-chain "
            "attack to CI/CD infrastructure."
        ),
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
        status="partially-implemented",
        description=(
            "GEC-6: C-007 (no shell=True), C-008 (URL/path validation) implement "
            "input validation. GEC-12-j: C-001 enforces minimal runtime dependencies."
        ),
    ),
    # ECR-k: Exploit Mitigation
    SOImplementation(
        so_id="so-reduce-impact-of-incident",
        ecr_id="ecr-k",
        controls=["C-005", "C-007", "C-015", "C-017", "C-046"],
        not_applicable=[
            "Compile-time mitigations (CFI, sandboxing) — not applicable to pure Python"
        ],
        gaps=["No documented exploit mitigation inventory (→ C-046 planned)"],
        status="planned",
        description=(
            "GEC-11: Python interpreter provides ASLR/DEP/stack-canaries (OS-level). "
            "dfetch: no eval/exec of remote content; constant-time comparison (C-005); "
            "shell=False (C-007); static analysis (C-015, C-017). "
            "C-046 (planned) formalises this inventory."
        ),
    ),
    # ECR-l: Monitoring and Logging
    SOImplementation(
        so_id="so-log-security-relevant-activities",
        ecr_id="ecr-l",
        controls=["C-036"],
        gaps=[
            "No persistent security event log (LGM-2/3/4 gap)",
            "No opt-out for logging — dfetch does not log by default",
        ],
        status="partially-implemented",
        description=(
            "LGM-1: dfetch logs warnings to stderr during a run but does not persist "
            "them. LGM-6: C-036 ensures credentials are not logged."
        ),
    ),
    SOImplementation(
        so_id="so-monitor-security-relevant-activities",
        ecr_id="ecr-l",
        controls=["C-009"],
        not_applicable=["NMM-1 (no ambient network monitoring)"],
        status="partially-implemented",
        description=(
            "MON-1: C-009 (plaintext transport detection) monitors for insecure "
            "connections at runtime and surfaces warnings to the user."
        ),
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
        gaps=[
            "No built-in delete command for .dfetch_data.yaml "
            "(DLM-1 gap; user deletes manually)"
        ],
        status="partially-implemented",
        description=(
            "DLM-1: dfetch stores only dependency metadata (no personal data). "
            "Users can permanently delete .dfetch_data.yaml and vendored directories."
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
        controls=["C-015", "C-016"],
        gaps=["No formal patch SLA defined", "No backport/LTS commitment documented"],
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
        controls=["MIT licence", "PyPI"],
        gaps=["No support period or LTS policy documented"],
        status="partially-implemented",
    ),
]
