
.. _security:

Security Model
==============

.. note::

  This document is a living artifact of the *dfetch* project, subject to ongoing updates as the project evolves.
  It is intended to provide transparency into the security considerations and design decisions of *dfetch*, and
  to serve as a reference for users, contributors, and downstream integrators. It is created to the best of the maintainers'
  knowledge and abilities, but is not a formal security audit or guarantee. Users are encouraged to review the document, its claims
  and dfetch itself critically, and provide feedback or contributions to enhance its accuracy and completeness.

This page documents the security design of *dfetch* across its full software
development lifecycle (SDLC): from source contribution through CI/CD,
PyPI distribution, and runtime execution in developer and build
environments.

The model is aligned with the `Cyber Resilience Act (CRA)`_ and the
`EN 40000`_ series of cybersecurity standards, using STRIDE as the threat
classification methodology. It is inspired by the `ENISA Security by Design and Default Playbook`_.

.. _`Cyber Resilience Act (CRA)`: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R2847
.. _`EN 40000`: https://www.cencenelec.eu/media/CEN-CENELEC/Events/Webinars/2025/2025-03-10_webinar_cyberresilience_act.pdf
.. _`ENISA Security by Design and Default Playbook`: https://www.enisa.europa.eu/sites/default/files/2026-03/ENISA_Secure_By_Design_and_Default_Playbook_v0.4_draft_for_consultation.pdf

The threat model is split into two focused modules:

- **Supply-chain model** — covers source
  contribution, CI/CD, build, PyPI distribution, and consumer installation.
- **Runtime-usage model** — covers post-install
  invocation: manifest reading, VCS/archive fetching, patching, vendoring,
  and reporting.

Product Security Context
------------------------

This section is the *Product Security Context note* required by
prEN 40000-1-2 §6.2. It establishes the foundation on which all
subsequent asset, threat, and control analysis is built.

Product and manufacturer identification
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :stub-columns: 1
   :widths: 30 70

   * - Product name
     - dfetch
   * - Current series
     - 0.x (pre-1.0, API not frozen)
   * - Maintainer
     - Ben Spoor
   * - Distribution channel
     - PyPI (``pip install dfetch``); GitHub Releases (stand-alone binary)
   * - Source repository
     - https://github.com/dfetch-org/dfetch
   * - License
     - MIT
   * - CRA applicability
     - dfetch is developed and distributed as a non-commercial open-source project.
       Under the Cyber Resilience Act, applicability depends on whether software
       is placed on the market in the context of a commercial activity.
       As of 2026-05-02, dfetch is not monetized and is not offered as part
       of a commercial service. However, CRA obligations may become applicable
       in downstream contexts where third parties integrate dfetch into commercial
       products, in which case those manufacturers may retain due diligence
       responsibilities under Article 13(5).

Intended purpose, foreseeable use, and reasonably foreseeable misuse (IPFRU)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

*Intended purpose*: fetch and vendor external source-code dependencies (from
Git repositories, SVN repositories, or plain archive URLs) as plain files into
a project repository. dfetch reads a declarative manifest (``dfetch.yaml``),
resolves each declared dependency to the requested revision, copies the source
tree to the declared destination path, and records metadata for subsequent
up-to-date checks.

*Foreseeable use*: invoked interactively on a developer workstation, or
non-interactively inside CI/CD pipelines (GitHub Actions, GitLab CI, Jenkins, etc.)
to reproduce a deterministic dependency state.

*Reasonably foreseeable misuse*: the following are the principal harms *dfetch*
aims to protect against. They are acknowledged here as priorities; the specific
threats that realise them and the corresponding responses are modelled in the
threat models below.

- **Credential and secret exfiltration in CI/CD.** When *dfetch* runs
  non-interactively in a pipeline holding registry tokens, signing keys, or cloud
  credentials, a compromised or intentionally malicious upstream source could read
  and exfiltrate those secrets.
- **Resource exhaustion from hostile archives.** A crafted archive (for example a
  decompression bomb) can expand to an extreme size or member count on extraction,
  exhausting disk or memory and denying service to the developer or build host.
- **Introduction of vulnerable or malicious code into the superproject.** More
  subtle than denial of service: an attacker-controlled upstream may ship source
  carrying latent vulnerabilities or backdoors that are vendored into the consuming
  project and propagated into downstream products.
- **Destruction or overwrite of files outside the destination folder.** A malicious
  manifest destination path, or hostile archive entries, could write, overwrite, or
  delete files outside the intended vendoring directory on the end-user machine.

Threat Models
-------------

The following pages document the two threat models in detail. Each page is
generated from the corresponding Python module in ``security/`` — see
`security/README.md <https://github.com/dfetch-org/dfetch/blob/main/security/README.md>`_
for instructions on regenerating them.

.. toctree::
   :maxdepth: 1

   threat_model_supply_chain
   threat_model_usage
   compliance_track
   control_register

CRA Compliance
--------------

The :doc:`compliance_track` page maps all 13 CRA Annex I Part I essential
requirements (ECR-a through ECR-m) through prEN 40000-1-4 Security Objectives
to dfetch's implemented controls.  It also covers the seven Part II
vulnerability-handling requirements via prEN 40000-1-3.

The three-tier traceability model is::

   CRA Annex I Essential Requirement (ECR-a … ECR-m)
           ↓
   prEN 40000-1-4 Security Objective (SO.*)
           ↓
   dfetch control (C-001 … C-046) or documented gap

Three compliance-only controls address CRA requirements not independently
surfaced by the risk models:

- :ref:`C-043 <c-043>` (release-gate CVE check) — ECR-a / SO.VulnerabilityManagementProcess → GEC-1
- :ref:`C-044 <c-044>` (data minimisation policy) — ECR-g / SO.DataMinimization → DTM-1
- :ref:`C-046 <c-046>` (exploit mitigation inventory) — ECR-k / SO.ReduceImpactOfIncident → GEC-11

Machine-readable OSCAL 1.1.2 artifacts are kept alongside the source:

- `security/cra_pren_4000014_oscal_catalog.json <https://github.com/dfetch-org/dfetch/blob/main/security/cra_pren_4000014_oscal_catalog.json>`_ — prEN 40000-1-4 catalog
  (derived from the CEN/CLC/JTC 13 WG 9 deep-dive session, March 2026)
- `security/dfetch.component-definition.json <https://github.com/dfetch-org/dfetch/blob/main/security/dfetch.component-definition.json>`_ — dfetch Component Definition

The complete list of all controls is on the :doc:`control_register` page.
