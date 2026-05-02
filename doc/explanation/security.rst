
.. _security:

Security Model
==============

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
     - Ben Spoor — dfetch@spoor.cc
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

*Reasonably foreseeable misuse*:

- A manifest crafted with a malicious ``dst:`` path could attempt to write
  files outside the project root (path traversal). dfetch mitigates this through
  `check_no_path_traversal()` applied to all file system write operations.
- A manifest pointing to an attacker-controlled upstream may introduce malicious
  source code into the build pipeline. This is a primary supply-chain risk; the
  optional `integrity.hash` field can be used as a mitigation for archive-based
  sources to provide content integrity validation.
- Execution in CI environments with insufficient network or secret isolation may
  allow exfiltration risks if upstream sources are compromised or intentionally
  malicious.
