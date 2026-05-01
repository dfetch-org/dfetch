
.. _security:

Security Model
==============

This page documents the security design of *dfetch* across its full software
development lifecycle (SDLC): from source contribution through CI/CD,
PyPI distribution, and runtime execution in developer and embedded-build
environments.

The model is aligned with the `Cyber Resilience Act (CRA)`_ and the
`EN 18031`_ series of cybersecurity standards, using STRIDE as the threat
classification methodology.

.. _`Cyber Resilience Act (CRA)`: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R2847
.. _`EN 18031`: https://www.cenelec.eu/

The threat model is maintained as executable code in ``security/threat_model.py``
using the `pytm`_ framework.  Regenerate analysis output with:

.. code-block:: bash

   python -m security.threat_model --seq    # PlantUML sequence diagram (stdout)
   python -m security.threat_model --dfd    # Graphviz DFD (stdout)
   python -m security.threat_model --report # STRIDE findings report

.. note::

   The ``security/`` package is intentionally excluded from built wheels and is
   **not** installed by ``pip install dfetch[security]``.  These commands must
   be run from a source checkout with the repository root on ``PYTHONPATH`` (or
   simply from the repository root, where Python resolves the ``security``
   package automatically).

.. note::

   The ``--seq`` and ``--dfd`` commands require **PlantUML** and **Graphviz**
   to be installed on the system.  These are not Python packages and are not
   installed by ``pip install .[security]``.  Install them separately (e.g.
   ``apt install plantuml graphviz`` or via your platform package manager)
   before running the diagram commands.

.. _pytm: https://github.com/izar/pytm

.. note::

   This document covers **Phase 1: asset register and implemented controls**.
   STRIDE threat enumeration, risk scoring, and controls-gap mapping will be
   added in subsequent phases.


Product Security Context
------------------------

This section is the *Product Security Context note* required by
prEN 40000-1-2 §6.2 (Step 0 of the security-by-design methodology).  It
establishes the foundation on which all subsequent asset, threat, and control
analysis is built.

**1 — Product and manufacturer identification**

.. list-table::
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
     - dfetch is a non-commercial open-source project and is not legally subject
       to the Cyber Resilience Act.  This security model is maintained as a
       matter of good practice and transparency.  If the project is ever
       redistributed commercially or classified as a *Product with Digital
       Elements* (PDE) under Article 3(1) of Regulation (EU) 2024/2847, the
       obligations under Articles 13–16 would apply in full.

**2 — Intended purpose, foreseeable use, and reasonably foreseeable misuse (IPFRU)**

*Intended purpose*: fetch and vendor external source-code dependencies (from
Git repositories, SVN repositories, or plain archive URLs) as plain files into
a project repository.  dfetch reads a declarative manifest (``dfetch.yaml``),
resolves each declared dependency to the requested revision, copies the source
tree to the declared destination path, and records metadata for subsequent
up-to-date checks.

*Foreseeable use*: invoked interactively on a developer workstation, or
non-interactively inside a CI/CD pipeline (GitHub Actions, GitLab CI, Jenkins,
etc.) to reproduce a known dependency state.

*Reasonably foreseeable misuse*:

- A manifest crafted with a malicious ``dst:`` path could attempt to write
  files outside the project root (path-traversal).  dfetch mitigates this with
  ``check_no_path_traversal()`` applied to every file copy.
- A manifest pointing to an attacker-controlled upstream could deliver
  malicious source code to the consuming build.  This is the primary supply-
  chain threat; the ``integrity.hash`` field provides an optional mitigation
  for archive sources.
- Passing secret-bearing environment variables to dfetch in a CI environment
  with inadequate egress controls could allow exfiltration if a dependency
  source is compromised.

**3 — User roles**

.. list-table::
   :header-rows: 1
   :widths: 20 25 55

   * - Role
     - Typical actor
     - Responsibilities and trust level
   * - **Manifest author** (Developer)
     - Human software developer
     - Writes and reviews ``dfetch.yaml``; responsible for choosing upstream
       sources, pinning revisions, and enabling ``integrity.hash`` for archive
       dependencies.  Trusted at workstation invocation time.
   * - **CI runner** (Automated)
     - GitHub Actions workflow, GitLab CI job, Jenkins agent
     - Invokes ``dfetch update`` non-interactively to reproduce the declared
       dependency set.  Runs in an ephemeral, semi-trusted environment;
       credential access is governed by the CI platform's secret store.
   * - **Security / compliance operator**
     - Security engineer, auditor, legal/compliance team
     - Reviews ``dfetch check`` and ``dfetch report --sbom`` output for
       outdated dependencies, known-vulnerable components, or licence compliance.
       Read-only interaction with dfetch artifacts.

**4 — Operating environment**

- **Developer workstation**: Linux, macOS, or Windows; Python 3.10 +; ``git``
  and/or ``svn`` clients available on ``PATH``.  No network listener or
  persistent service is started.  dfetch exits after completing each command.
- **CI/CD pipeline**: ephemeral runner (GitHub Actions, GitLab CI, etc.);
  access to upstream VCS hosts and PyPI.  dfetch does not require root or
  elevated privileges.
- **No runtime daemon**: dfetch is a pure CLI tool.  It does not bind ports,
  start background services, write to system directories, or persist state
  beyond the vendor directory and ``.dfetch_data.yaml`` metadata files.
- **Network requirements**: outbound HTTPS or SSH to the VCS/archive hosts
  declared in the manifest.  No inbound connections.

**5 — Architecture and connectivity**

dfetch is a single-process Python CLI application with no embedded network
server, no plugin system, and no IPC interface.  Its communication surface is:

- *stdin / argv*: command-line arguments and interactive prompts (only during
  ``dfetch add``).
- *Filesystem (read)*: ``dfetch.yaml`` manifest; patch files; existing vendor
  directory.
- *Filesystem (write)*: vendor directory (fetched source); ``.dfetch_data.yaml``
  metadata files; report files (SARIF, JSON, CycloneDX).
- *Outbound network*: ``git fetch`` / ``svn export`` / ``urllib``-based HTTP GET
  to hosts declared in the manifest.  All connections are outbound only.

No credentials are stored by dfetch.  VCS authentication is delegated to the
OS/SSH agent, Git credential helper, or SVN auth cache.

**6 — External dependencies**

Runtime Python packages: ``PyYAML``, ``strictyaml``, ``rich``, ``tldextract``,
``sarif-om``, ``semver``, ``patch-ng``, ``cyclonedx-python-lib``,
``infer-license``.  System binaries: ``git`` (optional), ``svn`` (optional).
None of these dependencies handle PII or secrets on behalf of dfetch.

The CI/CD pipeline additionally depends on GitHub Actions marketplace actions
(all SHA-pinned) and ``pip``/``build`` for packaging.

**7 — Security assumptions and prerequisites**

#. The developer workstation is trusted at the time dfetch is invoked.  A
   compromised workstation is outside the scope of the dfetch threat model.
#. TLS certificate validation is performed by the OS trust store and the
   ``git`` / ``svn`` / ``urllib`` clients.  dfetch does not independently
   validate certificates.
#. The manifest (``dfetch.yaml``) is under version control and subject to code
   review.  An adversary with write access to the manifest can redirect fetches
   to attacker-controlled sources; this threat is addressed at the code-review
   boundary, not within dfetch itself.
#. dfetch is responsible only for *its own* security posture.  The security of
   fetched third-party source code is the responsibility of the manifest author
   who selects and pins each dependency.
#. HTTPS enforcement is the responsibility of the manifest author.  dfetch
   accepts ``http://``, ``svn://``, and other non-TLS scheme URLs as written —
   it does not upgrade or reject them.
#. No secrets are stored by dfetch.  Any secrets present in the CI environment
   are the responsibility of the CI platform's secret store and the workflow
   author.

**8 — Support period and data handling**

- *Support period*: the **latest released version** only.  No security patches
  are backported to older releases.  Users are responsible for upgrading.
- *Personal data*: dfetch does not collect, store, or transmit any personal
  data.  It does not implement analytics, telemetry, or error reporting.  The
  fetched source code may contain personal data (e.g. author email addresses in
  VCS history) — handling of that data is the responsibility of the consuming
  project, not dfetch.
- *Vulnerability reporting*: see ``SECURITY.md`` and ``security.txt`` in the
  repository root for the coordinated vulnerability disclosure (CVD) policy.


Scope and Assumptions
---------------------

The threat model spans six trust boundaries (see below) and covers:

- The dfetch manifest and runtime fetch operations (developer workstation and CI)
- The GitHub repository and pull-request workflow
- The GitHub Actions CI/CD pipelines (11 workflows)
- PyPI distribution via OIDC trusted publishing
- Consumer installation and build integration

Modelling assumptions:

#. Developer workstations are trusted at dfetch invocation time.
#. TLS certificate validation is delegated to the OS, git, or SVN client.
#. No runtime secrets are persisted to disk by dfetch itself.
#. GitHub Actions environments inherit the security posture of the GitHub-hosted runner.
#. The ``integrity.hash`` field in the manifest is **optional** — archive
   dependencies without it have no content-authenticity guarantee beyond TLS
   transport (which is itself absent for plain ``http://`` URLs).
#. Branch- and tag-pinned Git dependencies are **mutable references** — upstream
   force-pushes silently change fetched content without triggering a manifest diff.
#. The ``harden-runner`` egress policy is set to ``audit``, not ``block`` —
   outbound network connections from CI runners are logged but not prevented.
#. dfetch's own build and development dependencies are **not** installed with
   ``--require-hashes``, so a compromised PyPI mirror can substitute build tooling.


Trust Boundaries
----------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Boundary
     - Description
   * - **Local Developer Environment**
     - Developer workstation or local CI runner.  Assumed trusted at invocation
       time.  Hosts the manifest, vendor directory, metadata, and patch files.
   * - **GitHub Actions Infrastructure**
     - Microsoft-operated ephemeral runners executing the 11 CI/CD workflows.
       Semi-trusted: egress is audited but not blocked; secrets are inherited
       across workflows via ``secrets: inherit``.
   * - **Internet**
     - All traffic crossing the local/remote boundary.  TLS enforcement is the
       responsibility of the OS and VCS clients; dfetch does not enforce HTTPS
       on manifest URLs.
   * - **Remote VCS Infrastructure**
     - Upstream Git and SVN servers (GitHub, GitLab, Gitea, self-hosted).  Not
       controlled by the dfetch project; content is untrusted until verified.
   * - **PyPI / TestPyPI**
     - Python Package Index.  dfetch publishes via OIDC trusted publishing —
       no long-lived API token stored.
   * - **Archive Content Space**
     - Downloaded archive bytes before extraction validation.  Decompression-bomb
       and path-traversal checks enforce this boundary during extraction.


Asset Register
--------------

Assets follow the ISO/IEC 27005 taxonomy used by EN 18031: **Primary** (PA)
assets have direct business value; **Supporting** (SA) assets enable them;
**Environmental** (EA) assets are infrastructure dependencies.  The table
below is generated at build time from ``security/threat_model.py``.

.. pytm::
   :assets:


Data Flows
----------

The following data flows are defined in ``security/threat_model.py`` and
annotated with the security controls that are currently implemented.  The
table is generated at build time from the pytm model.

.. pytm::
   :dataflows:


Implemented Security Controls
-------------------------------

The following controls are already in place and are reflected in the
``controls.*`` annotations on each pytm element.  The table is generated
at build time from ``CONTROLS`` in ``security/threat_model.py``.

.. pytm::
   :controls:


Known Gaps and Residual Risks
------------------------------

The following gaps were identified during asset analysis.  They represent
areas where existing controls are absent or incomplete.  The table is
generated at build time from ``GAPS`` in ``security/threat_model.py``.

.. pytm::
   :gaps:
