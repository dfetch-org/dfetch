
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

Product and manufacturer identification
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

Actors are defined in ``security/threat_model.py`` and rendered below from
the pytm model.

.. pytm::
   :actors:

Operating environment
~~~~~~~~~~~~~~~~~~~~~


.. pytm::
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

Assumptions are maintained in ``security/threat_model.py`` and rendered below
from the pytm model.

.. pytm::
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


Data Flow Diagram
-----------------

The diagram below is generated at build time from the pytm model using
Graphviz.  It shows all trust boundaries, processes, data stores, and
data flows.

.. pytm::
   :dfd:


Sequence Diagram
----------------

The diagram below is generated at build time from the pytm model using
PlantUML.  It shows the temporal ordering of key interactions across
trust boundaries.

.. pytm::
   :seq:


Identified Threats
------------------

The following threats were identified against the dfetch system model.
They are defined in ``security/threats.json`` and evaluated against
pytm elements at build time.  The *Controls* column lists implemented
controls (``Cx-xxx``) that directly address each threat; a dash (``—``)
indicates a gap with no current control.

.. pytm::
   :threats:


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
