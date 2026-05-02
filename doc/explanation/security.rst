
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

The threat model is split into two focused modules:

- **Supply-chain model** (``security/tm_supply_chain.py``) — covers source
  contribution, CI/CD, build, PyPI distribution, and consumer installation.
- **Runtime-usage model** (``security/tm_usage.py``) — covers post-install
  invocation: manifest reading, VCS/archive fetching, patching, vendoring,
  and reporting.

Shared building blocks (trust-boundary factories, the ``Control`` dataclass,
assumption lists) live in ``security/tm_common.py``.

Both models use the `pytm`_ framework.

.. _pytm: https://github.com/owasp/pytm


Product Security Context
------------------------

This section is the *Product Security Context note* required by
prEN 40000-1-2 §6.2 (Step 0 of the security-by-design methodology).  It
establishes the foundation on which all subsequent asset, threat, and control
analysis is built.

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
     - dfetch is a non-commercial open-source project and is not legally subject
       to the Cyber Resilience Act.  This security model is maintained as a
       matter of good practice and transparency.  If the project is ever
       redistributed commercially or classified as a *Product with Digital
       Elements* (PDE) under Article 3(1) of Regulation (EU) 2024/2847, the
       obligations under Articles 13-16 would apply in full.

Intended purpose, foreseeable use, and reasonably foreseeable misuse (IPFRU)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

User roles
~~~~~~~~~~

**Supply-chain actors** (contributors, CI operators, and consumers of the
dfetch package itself):

.. pytm:: ../security/tm_supply_chain.py
   :actors:

**Runtime-usage actors** (developers and CI systems invoking dfetch):

.. pytm:: ../security/tm_usage.py
   :actors:

Operating environment
~~~~~~~~~~~~~~~~~~~~~

**Supply-chain trust boundaries:**

.. pytm:: ../security/tm_supply_chain.py
   :boundaries:

**Runtime-usage trust boundaries:**

.. pytm:: ../security/tm_usage.py
   :boundaries:

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

Architecture and connectivity
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

dfetch is a single-process Python CLI application with no embedded network
server, no plugin system, and no IPC interface. Its communication surface is:

- *stdin / argv*: command-line arguments and interactive prompts (only during
  ``dfetch add``).
- *Filesystem (read)*: ``dfetch.yaml`` manifest; patch files; existing vendor
  directory.
- *Filesystem (write)*: vendor directory (fetched source); ``.dfetch_data.yaml``
  metadata files; report files (SARIF, JSON, CycloneDX).
- *Outbound network*: ``git fetch`` / ``svn export`` / ``urllib``-based HTTP GET
  to hosts declared in the manifest.  All connections are outbound only.

No credentials are stored by dfetch. VCS authentication is delegated to the
OS/SSH agent, Git credential helper, or SVN auth cache.

External dependencies
~~~~~~~~~~~~~~~~~~~~~

Runtime Python packages: ``PyYAML``, ``strictyaml``, ``rich``, ``tldextract``,
``sarif-om``, ``semver``, ``patch-ng``, ``cyclonedx-python-lib``,
``infer-license``.  System binaries: ``git`` (optional), ``svn`` (optional).
None of these dependencies handle PII or secrets on behalf of dfetch.

The CI/CD pipeline additionally depends on GitHub Actions marketplace actions
(all SHA-pinned) and ``pip``/``build`` for packaging.

Security assumptions and prerequisites
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Supply-chain assumptions:**

.. pytm:: ../security/tm_supply_chain.py
   :assumptions:

**Runtime-usage assumptions:**

.. pytm:: ../security/tm_usage.py
   :assumptions:

Support period and data handling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- *Support period*: the **latest released version** only.  No security patches
  are backported to older releases.  Users are responsible for upgrading.
- *Personal data*: dfetch does not collect, store, or transmit any personal
  data.  It does not implement analytics, telemetry, or error reporting.  The
  fetched source code may contain personal data (e.g. author email addresses in
  VCS history) — handling of that data is the responsibility of the consuming
  project, not dfetch.
- *Vulnerability reporting*: see ``SECURITY.md`` and ``security.txt`` in the
  repository root for the coordinated vulnerability disclosure (CVD) policy.


Supply Chain Security
---------------------

Covers the pre-install lifecycle: code contribution → CI/CD → build
(wheel / sdist) → PyPI distribution → consumer installation.

.. rubric:: Asset Register

.. pytm:: ../security/tm_supply_chain.py
   :assets:

.. rubric:: Data Flows

.. pytm:: ../security/tm_supply_chain.py
   :dataflows:

.. rubric:: Data Flow Diagram

.. pytm:: ../security/tm_supply_chain.py
   :dfd:

.. rubric:: Sequence Diagram

.. pytm:: ../security/tm_supply_chain.py
   :seq:

.. rubric:: Identified Threats

The following threats were identified against the supply-chain model.  They
are defined in ``security/threats.json`` and evaluated against pytm elements
at build time.  The *Controls* column lists implemented controls (``C-xxx``)
that directly address each threat; a dash (``—``) indicates a gap with no
current control.

.. pytm:: ../security/tm_supply_chain.py
   :threats:

.. rubric:: Implemented Security Controls

.. pytm:: ../security/tm_supply_chain.py
   :controls:

.. rubric:: Known Gaps and Residual Risks

.. pytm:: ../security/tm_supply_chain.py
   :gaps:


Runtime Usage Security
----------------------

Covers the post-install lifecycle: manifest reading → VCS/archive fetching
→ patch application → vendored-file writing → report generation.

.. rubric:: Asset Register

.. pytm:: ../security/tm_usage.py
   :assets:

.. rubric:: Data Flows

.. pytm:: ../security/tm_usage.py
   :dataflows:

.. rubric:: Data Flow Diagram

.. pytm:: ../security/tm_usage.py
   :dfd:

.. rubric:: Sequence Diagram

.. pytm:: ../security/tm_usage.py
   :seq:

.. rubric:: Identified Threats

The following threats were identified against the runtime-usage model.
They are defined in ``security/threats.json`` and evaluated against pytm
elements at build time.

.. pytm:: ../security/tm_usage.py
   :threats:

.. rubric:: Implemented Security Controls

.. pytm:: ../security/tm_usage.py
   :controls:

.. rubric:: Known Gaps and Residual Risks

.. pytm:: ../security/tm_usage.py
   :gaps:
