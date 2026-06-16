.. _compliance_track:

CRA Compliance
==============

.. note::

   dfetch is **non-commercial open-source software** and is exempt from
   mandatory CRA obligations under Recital 18 of Regulation (EU) 2024/2847.
   This document is produced voluntarily under Article 13(5) to support
   downstream integrators who must account for open-source components in
   their own conformity assessments.

This page provides three-tier traceability from the CRA Annex I essential
requirements through the prEN 40000-1-4 Security Objectives to the
concrete dfetch controls or documented gaps::

   CRA Annex I Essential Requirement (ECR-a … ECR-m)
           ↓
   prEN 40000-1-4 Security Objective (SO.*)
           ↓
   dfetch control (C-001 … C-046) or documented gap

Machine-readable OSCAL 1.1.2 artifacts are kept alongside the source:

- `security/cra_pren_4000014_oscal_catalog.json <https://github.com/dfetch-org/dfetch/blob/main/security/cra_pren_4000014_oscal_catalog.json>`_ — prEN 40000-1-4 catalog
- `security/dfetch.component-definition.json <https://github.com/dfetch-org/dfetch/blob/main/security/dfetch.component-definition.json>`_ — dfetch Component Definition

The full list of all controls is available on the :doc:`control_register` page.

.. rubric:: Status key

.. list-table::
   :widths: 10 90

   * - ✓
     - Implemented — control satisfies the objective fully.
   * - ⚠
     - Partial — control exists but a gap remains (see Gaps column).
   * - N/A
     - Not applicable — the objective does not apply to dfetch.

----

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
     - This compliance document is produced voluntarily under Article 13(5) to support downstream integrators who must account for open-source components in their own CRA conformity assessments.

----

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
     - Process standard covering risk-based product security across the lifecycle. The Product Security Context (§6.2) is documented in :doc:`security`. The threat models (`tm_supply_chain.py <https://github.com/dfetch-org/dfetch/blob/main/security/tm_supply_chain.py>`_, `tm_usage.py <https://github.com/dfetch-org/dfetch/blob/main/security/tm_usage.py>`_) implement §6.3–§6.6.
     - —
   * - prEN 40000-1-3
     - Vulnerability Handling Requirements
     - Yes
     - Covers CRA Annex I Part II vulnerability handling obligations. Addressed in the Part II table below via `SECURITY.md <https://github.com/dfetch-org/dfetch/blob/main/SECURITY.md>`_, SBOM (:ref:`C-022 <c-022>`), and dependency-review CI (:ref:`C-016 <c-016>`).
     - No formal patch SLA or LTS backport policy defined.
   * - prEN 40000-1-4
     - Generic Security Requirements (draft, indicative publication October 2027)
     - Yes
     - Primary standard for this document. Maps CRA Annex I Part I Art. 2(a)–(m) to Security Objectives (SO.\*) and Technical Controls (GEC-\*, SUM-\*, etc.). The catalog is included as `security/cra_pren_4000014_oscal_catalog.json <https://github.com/dfetch-org/dfetch/blob/main/security/cra_pren_4000014_oscal_catalog.json>`_.
     - Standard is in draft; final clause numbering may change.
   * - EN 18031-1/2:2024
     - Common security requirements for radio equipment (basis of prEN 40000-1-4)
     - Yes
     - prEN 40000-1-4 builds on EN 18031. Many technical controls (GEC-\*, SUM-\*, AUM-\*, SSM-\*, SCM-\*) originate from EN 18031. dfetch's applicability is assessed at the prEN 40000-1-4 SO level.
     - —
   * - ETSI EN 303 645 V3.1.3
     - Cyber Security for Consumer Internet of Things
     - No
     - IoT-specific standard. dfetch is a developer CLI tool with no IoT device functionality, physical interfaces, or consumer IoT use case.
     - —

----

Part I — Product Security Requirements (ECR-a to ECR-m)
--------------------------------------------------------

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
     - :ref:`C-015 <c-015>`, :ref:`C-016 <c-016>`, :ref:`C-017 <c-017>`, :ref:`C-022 <c-022>`, :ref:`C-043 <c-043>`
     - —
     - ✓ Implemented
   * - **ECR-B** — Be made available on the market with a secure by default configuration, including the possibility to reset the product to its original state.
     - SO.SecureDefaultConfiguration
     - :ref:`C-001 <c-001>`, :ref:`C-002 <c-002>`
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
     - :ref:`C-040 <c-040>`
     - —
     - ✓ Implemented
   * -
     - SO.PostponeUpdates
     - —
     - —
     - — N/A
   * - **ECR-D** — Ensure protection from unauthorised access by appropriate control mechanisms including authentication, identity or access management systems, and report on possible unauthorised access.
     - SO.AccessControl
     - :ref:`C-006 <c-006>`, :ref:`C-036 <c-036>`
     - —
     - ⚠ Partial
   * -
     - SO.AccessControlReport
     - :ref:`C-009 <c-009>`
     - No persistent log of unauthorised access attempts
     - ⚠ Partial
   * - **ECR-E** — Protect the confidentiality of stored, transmitted or otherwise processed data by state-of-the-art mechanisms such as encryption at rest and in transit.
     - SO.DataStoredConfidentiality
     - :ref:`C-036 <c-036>`
     - —
     - ✓ Implemented
   * -
     - SO.DataProcessedConfidentiality
     - :ref:`C-005 <c-005>`, :ref:`C-034 <c-034>`
     - —
     - ✓ Implemented
   * -
     - SO.DataTransmittedConfidentiality
     - :ref:`C-005 <c-005>`, :ref:`C-009 <c-009>`
     - —
     - ✓ Implemented
   * -
     - SO.ComAuth
     - :ref:`C-003 <c-003>`, :ref:`C-004 <c-004>`, :ref:`C-009 <c-009>`
     - —
     - ✓ Implemented
   * -
     - SO.SecureProvisioning
     - :ref:`C-005 <c-005>`
     - —
     - ⚠ Partial
   * - **ECR-F** — Protect the integrity of stored, transmitted or otherwise processed data, commands, programs and configuration against unauthorised manipulation or modification, and report on corruptions.
     - SO.DataStoredIntegrity
     - :ref:`C-005 <c-005>`
     - Integrity hash opt-in only; not enforced by default for git/svn
     - ⚠ Partial
   * -
     - SO.DataProcessedIntegrity
     - :ref:`C-005 <c-005>`, :ref:`C-034 <c-034>`
     - —
     - ✓ Implemented
   * -
     - SO.DataTransmittedIntegrity
     - :ref:`C-003 <c-003>`, :ref:`C-004 <c-004>`
     - No end-to-end hash for git/svn transport beyond TLS/SSH channel integrity
     - ⚠ Partial
   * -
     - SO.IntegrityReport
     - :ref:`C-009 <c-009>`
     - No persistent integrity-violation log
     - ⚠ Partial
   * - **ECR-G** — Process only data, personal or other, that are adequate, relevant and limited to what is necessary in relation to the intended purpose of the product with digital elements (data minimisation).
     - SO.DataMinimization
     - :ref:`C-044 <c-044>`
     - —
     - ✓ Implemented
   * - **ECR-H** — Protect the availability of essential and basic functions, also after an incident, including through resilience and mitigation measures against denial-of-service attacks.
     - SO.IncidentRecovery
     - —
     - —
     - — N/A
   * -
     - SO.IncidentResilience
     - :ref:`C-002 <c-002>`, :ref:`C-007 <c-007>`
     - No timeout on VCS operations (potential resource exhaustion)
     - ⚠ Partial
   * - **ECR-I** — Minimise the negative impact by the products themselves or connected devices on the availability of services provided by other devices or networks.
     - SO.LimitExternalImpact
     - :ref:`C-001 <c-001>`, :ref:`C-007 <c-007>`
     - —
     - ⚠ Partial
   * -
     - SO.PreventAttackPropagation
     - :ref:`C-001 <c-001>`, :ref:`C-008 <c-008>`
     - —
     - ✓ Implemented
   * -
     - SO.MonitorExternalImpact
     - —
     - —
     - — N/A
   * - **ECR-J** — Be designed, developed and produced to limit attack surfaces, including external interfaces.
     - SO.ReduceAttackSurface
     - :ref:`C-001 <c-001>`, :ref:`C-003 <c-003>`, :ref:`C-004 <c-004>`, :ref:`C-007 <c-007>`, :ref:`C-008 <c-008>`
     - —
     - ⚠ Partial
   * - **ECR-K** — Be designed, developed and produced to reduce the impact of an incident using appropriate exploitation mitigation mechanisms and techniques.
     - SO.ReduceImpactOfIncident
     - :ref:`C-005 <c-005>`, :ref:`C-007 <c-007>`, :ref:`C-015 <c-015>`, :ref:`C-017 <c-017>`, :ref:`C-046 <c-046>`
     - —
     - ✓ Implemented
   * - **ECR-L** — Provide security related information by recording and monitoring relevant internal activity, including the access to or modification of data, services or functions, with an opt-out mechanism for the user.
     - SO.LogSecurityRelevantActivities
     - :ref:`C-036 <c-036>`
     - No persistent security event log (LGM-2/3/4 gap); No opt-out for logging — dfetch does not log by default
     - ⚠ Partial
   * -
     - SO.MonitorSecurityRelevantActivities
     - :ref:`C-009 <c-009>`
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

----

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
     - :ref:`C-021 <c-021>`, :ref:`C-022 <c-022>`
     - —
     - ✓ Implemented
   * - Part II §2
     - Address vulnerabilities without delay; provide free security updates.
     - :ref:`C-015 <c-015>`, :ref:`C-016 <c-016>`, `SECURITY.md <https://github.com/dfetch-org/dfetch/blob/main/SECURITY.md>`_
     - No LTS backport policy (latest release only — documented in `SECURITY.md <https://github.com/dfetch-org/dfetch/blob/main/SECURITY.md>`_)
     - ⚠ Partial
   * - Part II §3
     - Apply effective coordinated vulnerability disclosure (CVD) policy.
     - `SECURITY.md <https://github.com/dfetch-org/dfetch/blob/main/SECURITY.md>`_
     - —
     - ✓ Implemented
   * - Part II §4
     - Report actively exploited vulnerabilities to national CSIRT and ENISA.
     - —
     - —
     - — N/A
   * - Part II §5
     - Publish coordinated vulnerability disclosure policy.
     - `SECURITY.md <https://github.com/dfetch-org/dfetch/blob/main/SECURITY.md>`_
     - —
     - ✓ Implemented
   * - Part II §6
     - Share information on vulnerabilities in integrated components.
     - :ref:`C-022 <c-022>`, :ref:`C-016 <c-016>`
     - No proactive downstream notification process
     - ⚠ Partial
   * - Part II §7
     - Provide security updates free of charge for the support period.
     - MIT licence, PyPI, `SECURITY.md <https://github.com/dfetch-org/dfetch/blob/main/SECURITY.md>`_
     - —
     - ✓ Implemented

----

Gap Analysis — Compliance-Only Controls
----------------------------------------

Three compliance-only controls address CRA requirements not independently covered by the risk models.

**:ref:`C-043 <c-043>` — Release-gate CVE check (ECR-a, SO.VulnerabilityManagementProcess → GEC-1)**

dfetch's CI detects vulnerabilities at commit time (:ref:`C-015 <c-015>`, :ref:`C-016 <c-016>`, :ref:`C-017 <c-017>`). :ref:`C-043 <c-043>` completes the coverage: the publish workflow runs ``pip-audit`` against the project's runtime dependencies via the OSV database and blocks the release if any known vulnerability is found.

**:ref:`C-044 <c-044>` — Data minimisation policy (ECR-g, SO.DataMinimization → DTM-1)**

dfetch processes dependency metadata only. The ``.dfetch_data.yaml`` file stores: ``remote_url`` (credentials stripped by :ref:`C-036 <c-036>`), ``revision``, optional ``integrity.hash``, and ``last_fetch`` timestamp. Each field is functionally necessary for ``dfetch check`` and ``dfetch freeze``. No personal data is collected; no telemetry is sent. :ref:`C-044 <c-044>` formalises this assertion as a documented policy.

**:ref:`C-046 <c-046>` — Exploit mitigation inventory (ECR-k, SO.ReduceImpactOfIncident → GEC-11)**

prEN 40000-1-4 ECR-k requires documenting applicable exploit mitigation techniques. For dfetch (pure Python):

- **ASLR / DEP / stack canaries**: provided by CPython and the OS;   not in dfetch's control but inherited.
- **No eval/exec of remote content**: dfetch never evaluates fetched   content as code.
- **Constant-time comparison** (:ref:`C-005 <c-005>`): HMAC-based integrity hash uses   ``hmac.compare_digest``.
- **No shell injection** (:ref:`C-007 <c-007>`): all subprocess calls use ``shell=False``.
- **Input validation** (:ref:`C-008 <c-008>`): URL scheme, path, and revision inputs   are validated.
- **Static analysis** (:ref:`C-015 <c-015>`, :ref:`C-017 <c-017>`): CodeQL and bandit gate every commit.
- CFI, sandboxing, and signed-execution policies are not applicable to   a pure-Python tool.

----

OSCAL Artifacts
---------------

The OSCAL 1.1.2 Component Definition references the catalog file and can be
regenerated with:

.. code-block:: bash

   python -m security.compliance \\
       --component security/dfetch.component-definition.json \\
       --rst > doc/explanation/compliance_track.rst
