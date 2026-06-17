
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
`EN 40000`_ series of cybersecurity standards, using `STRIDE`_ as the threat
classification methodology. It is inspired by the `ENISA Security by Design and Default Playbook`_.

.. _`Cyber Resilience Act (CRA)`: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R2847
.. _`EN 40000`: https://www.cencenelec.eu/areas-of-work/cen-cenelec-topics/cybersecurity/
.. _`STRIDE`: https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats
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
       products, in which case those manufacturers bear their own Article 13
       obligations to assess and document the security of components they integrate,
       including open-source dependencies.

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

.. _risk-rating-methodology:

Risk Rating Methodology
-----------------------

Both threat models use a qualitative two-axis risk framework aligned with
`BSI TR-03183-1 §5.3 <https://www.bsi.bund.de/SharedDocs/Downloads/EN/BSI/Publications/TechGuidelines/TR03183/BSI-TR-03183-1.pdf>`_
(Cyber Resilience Requirements for Manufacturers, Chapter 5).

Each threat entry carries two independent ratings:

**Severity (Sev)** — the maximum potential impact if the threat is fully
realised, assessed without regard to likelihood or existing controls.
Determined from the Confidentiality / Integrity / Availability ratings of
the targeted asset and the scope of harm to downstream consumers.

**Risk** — the *residual* risk after factoring in the likelihood of
successful exploitation (attacker capability, required access, known
exploitation evidence) and any controls already partially in place.
Risk can therefore be lower than Severity when the attack path is
constrained, and must be reassessed whenever the control set changes.

.. list-table::
   :header-rows: 1
   :widths: 12 20 68

   * - Rating
     - Label
     - Guidance (BSI TR-03183-1 §5.3)

   * - 🟢L
     - Low
     - Negligible impact or extremely unlikely. No mandatory control action; document and monitor.

   * - 🟡M
     - Medium
     - Moderate impact or realistic but non-trivial exploit path. Controls advisable; track in backlog.

   * - 🟠H
     - High
     - Significant impact or credible attack path with meaningful probability. Controls required before next release.

   * - 🔴VH
     - Very High
     - Severe impact (system compromise, data exfiltration) or well-documented exploit path. Priority controls required.

   * - 🔴C
     - Critical
     - Catastrophic, near-certain potential (e.g. unencrypted channel with no compensating control). Immediate mitigation required; accept decision requires explicit sign-off.

The risk treatment decisions (Mitigate / Accept / Transfer) in each threat
table follow the risk treatment vocabulary of BSI TR-03183-1: an
**Accept** decision requires explicit rationale citing the assumption under
which the residual risk is acceptable, documented alongside the threat entry.

Threat Models
-------------

The two threat models below cover the full lifecycle of *dfetch*. Both are
generated from the Python modules in ``security/``; see
`security/README.md <https://github.com/dfetch-org/dfetch/blob/main/security/README.md>`_
for regeneration instructions.

.. toctree::
   :maxdepth: 1

   threat_model_supply_chain
   threat_model_usage

CRA Compliance
--------------

The :doc:`compliance_track` page provides full three-tier traceability from all
13 CRA Annex I Part I essential requirements (ECR-a through ECR-m) through
prEN 40000-1-4 Security Objectives to dfetch's implemented controls, including
machine-readable OSCAL artifacts and the gap analysis for compliance-only
controls.  It also covers the seven Part II vulnerability-handling requirements
via prEN 40000-1-3.  The complete list of all controls is on the
:doc:`control_register` page.

.. toctree::
   :maxdepth: 1

   compliance_track
   control_register

Further Reading
---------------

Cyber Resilience Act
~~~~~~~~~~~~~~~~~~~~

- `Regulation (EU) 2024/2847 — Cyber Resilience Act <https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R2847>`_ —
  the legislative text; Annex I Part I lists the 13 essential requirements (ECR-a … ECR-m)
  and Part II the seven vulnerability-handling requirements.
- `EU Commission CRA overview <https://digital-strategy.ec.europa.eu/en/policies/cyber-resilience-act>`_ —
  accessible summary of scope, obligations, and timeline.
- `CRA draft guidance, March 2026 (Ares(2026)2319816) <https://digital-strategy.ec.europa.eu/en/news/commission-publishes-feedback-draft-guidance-assist-companies-applying-cyber-resilience-act>`_ —
  Commission guidance covering free and open-source software, remote data processing, and support periods.
- `BSI TR-03183-1: Cyber Resilience Requirements for Manufacturers <https://www.bsi.bund.de/SharedDocs/Downloads/EN/BSI/Publications/TechGuidelines/TR03183/BSI-TR-03183-1.pdf>`_ —
  practical risk-based guidance aligned with CRA; the risk-rating framework above is derived from this document.

EN 40000 harmonised standards
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The EN 40000 family is being developed by CEN/CLC/JTC 13 to provide harmonised
standards under the CRA. Once published in the OJEU, compliance with them confers a
presumption of conformity with the corresponding CRA essential requirements.

- `CEN/CENELEC cybersecurity standards page <https://www.cencenelec.eu/areas-of-work/cen-cenelec-topics/cybersecurity/>`_ —
  overview of the EN 40000 work programme (prEN 40000-1-1 through 40000-1-4).
- `CEN/CENELEC CRA webinar slides (March 2025) <https://www.cencenelec.eu/media/CEN-CENELEC/Events/Webinars/2025/2025-03-10_webinar_cyberresilience_act.pdf>`_ —
  explains how each part of EN 40000 maps to CRA obligations and the Security Objectives (SO.*) in prEN 40000-1-4.

Threat modelling
~~~~~~~~~~~~~~~~

- `STRIDE methodology <https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats>`_ —
  Microsoft's six-category threat classification used to classify every entry in
  `security/threats.json <https://github.com/dfetch-org/dfetch/blob/main/security/threats.json>`_.
- `pytm — Pythonic Threat Modeling <https://github.com/izar/pytm>`_ —
  the library used by ``tm_supply_chain.py`` and ``tm_usage.py`` to define model elements
  and auto-generate threat findings.
- `ENISA Security by Design and Default Playbook <https://www.enisa.europa.eu/sites/default/files/2026-03/ENISA_Secure_By_Design_and_Default_Playbook_v0.4_draft_for_consultation.pdf>`_ —
  ENISA guidance that inspired the overall model structure.

OSCAL
~~~~~

`OSCAL (Open Security Controls Assessment Language) <https://pages.nist.gov/OSCAL/>`_ is a
set of NIST-published JSON/XML schemas for machine-readable security documentation.
dfetch uses OSCAL 1.1.2 for two artifacts:

- `OSCAL Catalog model <https://pages.nist.gov/OSCAL/reference/latest/catalog/>`_ —
  used by ``cra_pren_4000014_oscal_catalog.json`` to represent the prEN 40000-1-4
  security objectives as a structured catalog.
- `OSCAL Component Definition model <https://pages.nist.gov/OSCAL/reference/latest/component-definition/>`_ —
  used by ``dfetch.component-definition.json`` to describe how dfetch implements each
  control and maps it back to CRA essential requirements via SO.* objectives.

Security documentation pipeline
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For an overview of how this documentation set is produced — the threat-model
pipeline, compliance pipeline, release attestations, and the full artifact
inventory — see :doc:`security_pipeline`.

.. toctree::
   :hidden:

   security_pipeline
