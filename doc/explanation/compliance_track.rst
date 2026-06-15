.. _compliance_track:

CRA Compliance Track B
======================

.. note::

   dfetch is **non-commercial open-source software** and is exempt from
   mandatory CRA obligations under Recital 18 of Regulation (EU) 2024/2847.
   This document is produced voluntarily under Article 13(5) to support
   downstream integrators who must account for open-source components in
   their own conformity assessments.

Three-tier traceability::

   CRA Annex I Essential Requirement (ECR-a … ECR-m)
           ↓
   prEN 40000-1-4 Security Objective (SO.*)
           ↓
   dfetch control (C-001 … C-046) or documented gap

Machine-readable OSCAL 1.1.2 artifacts are kept alongside the source:

- ``security/cra_pren_4000014_oscal_catalog.json`` — prEN 40000-1-4 catalog
- ``security/dfetch.component-definition.json`` — dfetch Component Definition

Classification Decision
-----------------------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Criterion
     - Decision / Basis
   * - Product type
     - Software tool (CLI) — Python package distributed via PyPI
   * - CRA classification
     - Non-commercial open-source software (Recital 18 exemption)
   * - Legal basis
     - Article 3(14), Recital 18, Article 13(5) of Regulation (EU) 2024/2847
   * - Mandatory obligations
     - None — not a commercial product; no CE marking required
   * - Voluntary alignment
     - This Track B document is produced voluntarily under Article 13(5) to support downstream integrators who must account for open-source components in their own CRA conformity assessments.

Applicable Standards
--------------------

.. list-table::
   :header-rows: 1
   :widths: 18 25 6 35 16

   * - Standard
     - Full title
     - Applies
     - Scope note
     - Gap
   * - prEN 40000-1-2
     - Cyber Resilience Principles and Risk Management
     - Yes
     - Process standard covering risk-based product security across the lifecycle. The Product Security Context (§6.2) is documented in security.rst. Track A threat models (tm_supply_chain.py, tm_usage.py) implement §6.3–§6.6.
     - —
   * - prEN 40000-1-3
     - Vulnerability Handling Requirements
     - Yes
     - Covers CRA Annex I Part II vulnerability handling obligations. Addressed in the Part II table below via SECURITY.md, SBOM (C-022), and dependency-review CI (C-016).
     - No formal patch SLA or LTS backport policy defined.
   * - prEN 40000-1-4
     - Generic Security Requirements (draft, indicative publication October 2027)
     - Yes
     - Primary standard for this document. Maps CRA Annex I Part I Art. 2(a)–(m) to Security Objectives (SO.*) and Technical Controls (GEC-*, SUM-*, etc.). The catalog is included as security/cra_pren_4000014_oscal_catalog.json.
     - Standard is in draft; final clause numbering may change.
   * - EN 18031-1/2:2024
     - Common security requirements for radio equipment (basis of prEN 40000-1-4)
     - Yes
     - prEN 40000-1-4 builds on EN 18031. Many technical controls (GEC-*, SUM-*, AUM-*, SSM-*, SCM-*) originate from EN 18031. dfetch's applicability is assessed at the prEN 40000-1-4 SO level.
     - —
   * - ETSI EN 303 645 V3.1.3
     - Cyber Security for Consumer Internet of Things
     - No
     - IoT-specific standard. dfetch is a developer CLI tool with no IoT device functionality, physical interfaces, or consumer IoT use case.
     - —

Part I — Product Security Requirements (ECR-a to ECR-m)
-------------------------------------------------------

The table below summarises dfetch's implementation of each prEN 40000-1-4 Security Objective per CRA essential requirement.

.. list-table::
   :header-rows: 1
   :widths: 20 28 18 20 14

   * - CRA ECR
     - SO (prEN 40000-1-4)
     - dfetch controls
     - Gaps
     - Status
   * - **ECR-A** — Be made available on the market without known exploitable vulnerabilities.
     - SO.VulnerabilityManagementProcess
     - C-015, C-016, C-017, C-022
     - No CVE gate at release time (→ C-043 planned)
     - ⚠ Partial
   * - **ECR-B** — Be made available on the market with a secure by default configuration, including the possibility to reset the product to its original state.
     - SO.SecureDefaultConfiguration
     - C-001, C-002
     - —
     - ⚠ Partial
   * - 
     - SO.SecureStartupConfig
     - —
     - —
     - — N/A
   * - 
     - SO.FactoryReset
     - —
     - —
     - — N/A
   * - **ECR-C** — Ensure that vulnerabilities can be addressed through security updates, including automatic updates enabled by default, with an opt-out mechanism, user notification, and the option to postpone updates.
     - SO.Updateability
     - —
     - —
     - ✓ Implemented
   * - 
     - SO.AutomaticUpdates
     - —
     - —
     - — N/A
   * - 
     - SO.UserUpdateNotification
     - C-040
     - —
     - ✓ Implemented
   * - 
     - SO.PostponeUpdates
     - —
     - —
     - — N/A
   * - **ECR-D** — Ensure protection from unauthorised access by appropriate control mechanisms including authentication, identity or access management systems, and report on possible unauthorised access.
     - SO.AccessControl
     - C-006, C-036
     - —
     - ⚠ Partial
   * - 
     - SO.AccessControlReport
     - C-009
     - No persistent log of unauthorised access attempts
     - ⚠ Partial
   * - **ECR-E** — Protect the confidentiality of stored, transmitted or otherwise processed data by state-of-the-art mechanisms such as encryption at rest and in transit.
     - SO.DataStoredConfidentiality
     - C-036
     - —
     - ✓ Implemented
   * - 
     - SO.DataProcessedConfidentiality
     - C-005, C-034
     - —
     - ✓ Implemented
   * - 
     - SO.DataTransmittedConfidentiality
     - C-005, C-009
     - —
     - ✓ Implemented
   * - 
     - SO.ComAuth
     - C-003, C-004, C-009
     - —
     - ✓ Implemented
   * - 
     - SO.SecureProvisioning
     - C-005
     - —
     - ⚠ Partial
   * - **ECR-F** — Protect the integrity of stored, transmitted or otherwise processed data, commands, programs and configuration against unauthorised manipulation or modification, and report on corruptions.
     - SO.DataStoredIntegrity
     - C-005
     - Integrity hash opt-in only; not enforced by default for git/svn
     - ⚠ Partial
   * - 
     - SO.DataProcessedIntegrity
     - C-005, C-034
     - —
     - ✓ Implemented
   * - 
     - SO.DataTransmittedIntegrity
     - C-003, C-004
     - No end-to-end hash for git/svn transport beyond TLS/SSH channel integrity
     - ⚠ Partial
   * - 
     - SO.IntegrityReport
     - C-009
     - No persistent integrity-violation log
     - ⚠ Partial
   * - **ECR-G** — Process only data, personal or other, that are adequate, relevant and limited to what is necessary in relation to the intended purpose of the product with digital elements (data minimisation).
     - SO.DataMinimization
     - C-044
     - —
     - ○ Planned
   * - **ECR-H** — Protect the availability of essential and basic functions, also after an incident, including through resilience and mitigation measures against denial-of-service attacks.
     - SO.IncidentRecovery
     - —
     - —
     - — N/A
   * - 
     - SO.IncidentResilience
     - C-002, C-007
     - No timeout on VCS operations (potential resource exhaustion)
     - ⚠ Partial
   * - **ECR-I** — Minimise the negative impact by the products themselves or connected devices on the availability of services provided by other devices or networks.
     - SO.LimitExternalImpact
     - C-001, C-007
     - —
     - ⚠ Partial
   * - 
     - SO.PreventAttackPropagation
     - C-001, C-008
     - —
     - ✓ Implemented
   * - 
     - SO.MonitorExternalImpact
     - —
     - —
     - — N/A
   * - **ECR-J** — Be designed, developed and produced to limit attack surfaces, including external interfaces.
     - SO.ReduceAttackSurface
     - C-001, C-003, C-004, C-007, C-008
     - —
     - ⚠ Partial
   * - **ECR-K** — Be designed, developed and produced to reduce the impact of an incident using appropriate exploitation mitigation mechanisms and techniques.
     - SO.ReduceImpactOfIncident
     - C-005, C-007, C-015, C-017, C-046
     - No documented exploit mitigation inventory (→ C-046 planned)
     - ○ Planned
   * - **ECR-L** — Provide security related information by recording and monitoring relevant internal activity, including the access to or modification of data, services or functions, with an opt-out mechanism for the user.
     - SO.LogSecurityRelevantActivities
     - C-036
     - No persistent security event log (LGM-2/3/4 gap); No opt-out for logging — dfetch does not log by default
     - ⚠ Partial
   * - 
     - SO.MonitorSecurityRelevantActivities
     - C-009
     - —
     - ⚠ Partial
   * - 
     - SO.OptionDisableDataLogging
     - —
     - —
     - — N/A
   * - 
     - SO.OptionDisableDataMonitoring
     - —
     - —
     - — N/A
   * - **ECR-M** — Provide the possibility for users to securely and easily remove on a permanent basis all data and settings and, where such data can be transferred to other products or systems, ensure that this is done in a secure manner.
     - SO.SecureDataDeletion
     - —
     - —
     - ✓ Implemented
   * - 
     - SO.DataTransmittedConfidentiality
     - —
     - —
     - — N/A
   * - 
     - SO.DataTransmittedIntegrity
     - —
     - —
     - — N/A
   * - 
     - SO.ComAuth
     - —
     - —
     - — N/A

Part II — Vulnerability Handling (prEN 40000-1-3)
-------------------------------------------------

Part II requirements are addressed via prEN 40000-1-3. pii-04 is not applicable under Recital 18.

.. list-table::
   :header-rows: 1
   :widths: 10 32 18 24 12

   * - CRA ref
     - Requirement
     - dfetch controls
     - Gaps
     - Status
   * - Part II §1
     - Identify and document vulnerabilities and components (SBOM).
     - C-021, C-022
     - —
     - ✓ Implemented
   * - Part II §2
     - Address vulnerabilities without delay; provide free security updates.
     - C-015, C-016
     - No formal patch SLA defined; No backport/LTS commitment documented
     - ⚠ Partial
   * - Part II §3
     - Apply effective coordinated vulnerability disclosure (CVD) policy.
     - SECURITY.md
     - —
     - ✓ Implemented
   * - Part II §4
     - Report actively exploited vulnerabilities to national CSIRT and ENISA.
     - —
     - —
     - — N/A
   * - Part II §5
     - Publish coordinated vulnerability disclosure policy.
     - SECURITY.md
     - —
     - ✓ Implemented
   * - Part II §6
     - Share information on vulnerabilities in integrated components.
     - C-022, C-016
     - No proactive downstream notification process
     - ⚠ Partial
   * - Part II §7
     - Provide security updates free of charge for the support period.
     - MIT licence, PyPI
     - No support period or LTS policy documented
     - ⚠ Partial

Gap Analysis — Compliance-Only Controls
---------------------------------------

3 compliance-only controls address CRA requirements not independently covered by the Track A risk models.

**C-043 — Release-gate CVE check (ECR-a, SO.VulnerabilityManagementProcess → GEC-1)**

dfetch's CI detects vulnerabilities at commit time (C-015, C-016, C-017) but does not gate the release publish on a CVE scan of runtime dependencies. C-043 (planned) adds ``pip-audit`` or ``osv-scanner`` to the publish workflow.

**C-044 — Data minimisation policy (ECR-g, SO.DataMinimization → DTM-1)**

dfetch processes dependency metadata only. The ``.dfetch_data.yaml`` file stores: ``remote_url`` (credentials stripped by C-036), ``revision``, optional ``integrity.hash``, and ``last_fetch`` timestamp. Each field is functionally necessary for ``dfetch check`` and ``dfetch freeze``. No personal data is collected; no telemetry is sent. C-044 formalises this assertion as a documented policy.

**C-046 — Exploit mitigation inventory (ECR-k, SO.ReduceImpactOfIncident → GEC-11)**

prEN 40000-1-4 ECR-k requires documenting applicable exploit mitigation techniques. For dfetch (pure Python):

- **ASLR / DEP / stack canaries**: provided by CPython and the OS;   not in dfetch's control but inherited.
- **No eval/exec of remote content**: dfetch never evaluates fetched   content as code.
- **Constant-time comparison** (C-005): HMAC-based integrity hash uses   ``hmac.compare_digest``.
- **No shell injection** (C-007): all subprocess calls use ``shell=False``.
- **Input validation** (C-008): URL scheme, path, and revision inputs   are validated.
- **Static analysis** (C-015, C-017): CodeQL and bandit gate every commit.
- CFI, sandboxing, and signed-execution policies are not applicable to   a pure-Python tool.

Final Control Register
----------------------

All controls from Track A (risk-driven) and Track B (regulatory) merged and sorted. Track B controls (C-043–C-046) are marked accordingly.

.. list-table::
   :header-rows: 1
   :widths: 8 40 10 42

   * - ID
     - Name
     - Track
     - Reference
   * - C-001
     - Path-traversal prevention
     - Track A
     - dfetch/util/util.py
   * - C-002
     - Decompression-bomb protection
     - Track A
     - dfetch/vcs/archive.py
   * - C-003
     - Archive symlink validation
     - Track A
     - dfetch/vcs/archive.py
   * - C-004
     - Archive member type checks
     - Track A
     - dfetch/vcs/archive.py
   * - C-005
     - Integrity hash verification
     - Track A
     - dfetch/vcs/integrity_hash.py
   * - C-006
     - Non-interactive VCS
     - Track A
     - dfetch/vcs/git.py, dfetch/vcs/svn.py
   * - C-007
     - Subprocess safety
     - Track A
     - dfetch/util/cmdline.py
   * - C-008
     - Manifest input validation
     - Track A
     - dfetch/manifest/schema.py
   * - C-009
     - Actions commit-SHA pinning
     - Track A
     - .github/workflows/*.yml
   * - C-010
     - OIDC trusted publishing
     - Track A
     - .github/workflows/python-publish.yml
   * - C-011
     - Minimal workflow permissions
     - Track A
     - .github/workflows/*.yml
   * - C-012
     - persist-credentials: false
     - Track A
     - .github/workflows/*.yml
   * - C-013
     - Harden-runner (egress block)
     - Track A
     - .github/workflows/*.yml
   * - C-015
     - CodeQL static analysis
     - Track A
     - .github/workflows/codeql-analysis.yml
   * - C-016
     - Dependency review
     - Track A
     - .github/workflows/dependency-review.yml
   * - C-017
     - bandit security linter
     - Track A
     - pyproject.toml
   * - C-021
     - Sigstore SBOM attestation
     - Track A
     - —
   * - C-022
     - CycloneDX SBOM on PyPI
     - Track A
     - —
   * - C-024
     - ``secrets: inherit`` scope
     - Track A
     - —
   * - C-026
     - Consumer-side package provenance verification
     - Track A
     - doc/howto/verify-integrity.rst
   * - C-032
     - Consumer attestation verification pins to release tag ref
     - Track A
     - doc/howto/verify-integrity.rst
   * - C-033
     - Ref-scoped build cache keys isolate PR and release builds
     - Track A
     - .github/workflows/build.yml
   * - C-034
     - Hash algorithm allowlist (SHA-256/384/512 only)
     - Track A
     - dfetch/vcs/integrity_hash.py
   * - C-036
     - Persisted-metadata credential redaction
     - Track A
     - dfetch/project/metadata.py
   * - C-037
     - SLSA Source Provenance Attestation of repository governance controls
     - Track A
     - .github/workflows/source-provenance.yml
   * - C-038
     - Ancestry enforcement on dfetch main branch
     - Track A
     - .github/workflows/
   * - C-039
     - Source build provenance and VSA attestations
     - Track A
     - doc/howto/verify-integrity.rst
   * - C-040
     - Test result attestation on source archive
     - Track A
     - .github/workflows/test.yml
   * - C-041
     - Winget manifest PRs reviewed by community maintainers
     - Track A
     - .github/workflows/winget-publish.yml
   * - C-042
     - WINGET_TOKEN scoped to dedicated Winget environment
     - Track A
     - .github/workflows/winget-publish.yml
   * - C-043
     - Release-gate CVE check on runtime dependencies
     - Track B
     - .github/workflows/python-publish.yml (planned CI addition)
   * - C-044
     - Data minimisation policy
     - Track B
     - doc/explanation/compliance_track.rst (this document)
   * - C-046
     - Exploit mitigation inventory
     - Track B
     - doc/explanation/compliance_track.rst (this document)

OSCAL Artifacts
---------------

The OSCAL 1.1.2 Component Definition references the catalog file and can be
regenerated with:

.. code-block:: bash

   python -m security.compliance \\
       --component security/dfetch.component-definition.json \\
       --rst > doc/explanation/compliance_track.rst

