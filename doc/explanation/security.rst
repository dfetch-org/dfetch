
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

Assets are classified following the ISO/IEC 27005 taxonomy used by EN 18031:
**Primary** assets have direct value and direct harm upon compromise;
**Supporting** assets enable primary assets and degrade their security when
lost; **Environmental** assets are infrastructure dependencies.

Primary Assets
~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 8 28 14 50

   * - ID
     - Name
     - Classification
     - Description
   * - PA-01
     - dfetch Manifest (``dfetch.yaml``)
     - Sensitive
     - StrictYAML file declaring all upstream sources, version pins, destination
       paths, patch references, and optional integrity hashes.  Tampering
       redirects fetches to attacker-controlled sources.  Risk: the
       ``integrity.hash`` field is optional in the schema — archive dependencies
       can be declared without any content-authenticity guarantee.
   * - PA-02
     - Fetched Source Code
     - Sensitive
     - Third-party source written to the ``dst:`` path after extraction or
       checkout.  Becomes a direct build input for the consuming project.  A
       compromised upstream or MITM can inject malicious code that executes in
       the consumer's build system, test runner, or production binary.
   * - PA-03
     - Integrity Hash Record
     - Sensitive
     - ``integrity.hash:`` field in ``dfetch.yaml`` (``sha256|sha384|sha512:<hex>``).
       The sole trust anchor for archive-type dependencies; verified via
       ``hmac.compare_digest`` (constant-time).  Critical gap: the field is
       optional — its absence disables all content verification.  Git and SVN
       dependencies have no equivalent mechanism; authenticity relies entirely
       on transport security (TLS/SSH).
   * - PA-04
     - dfetch PyPI Package
     - Sensitive
     - Published wheel and source distribution on PyPI.  Published via OIDC
       trusted publishing — no long-lived API token stored.  Missing: no SLSA
       provenance attestation or Sigstore signature.  Compromise of the PyPI
       account or registry affects every consumer of dfetch.
   * - PA-05
     - SBOM Output (CycloneDX)
     - Restricted
     - CycloneDX JSON or XML produced by ``dfetch report -t sbom``.  Enumerates
       vendored components with PURL, license, and hash.  Falsification hides
       actual dependencies from downstream CVE scanners.  Note: this SBOM covers
       vendored dependencies only — dfetch itself has no machine-readable SBOM
       on PyPI, which CRA requires for distributed products.

Supporting Assets
~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 8 28 14 50

   * - ID
     - Name
     - Classification
     - Description
   * - SA-01
     - dfetch Process
     - Restricted
     - Running Python interpreter dispatching to update, check, diff, add,
       remove, patch, freeze, import, report, validate, and environment commands.
       Subprocess injection or dependency confusion could compromise build-time
       code execution.
   * - SA-02
     - VCS Credentials
     - Secret
     - SSH private keys, HTTPS Personal Access Tokens, SVN passwords.  Used to
       authenticate to private upstream repositories.  dfetch never persists
       these — managed by OS keychain or CI secret store.  Exfiltration via a
       compromised CI workflow step is the primary risk (harden-runner is in
       audit mode, not block mode).
   * - SA-03
     - Dependency Metadata (``.dfetch_data.yaml``)
     - Restricted
     - Per-dependency tracking files written after each successful fetch.
       Contain: remote URL, revision/branch/tag, hash, last-fetch timestamp.
       Read by ``dfetch check`` to detect outdated dependencies.  Tampering can
       suppress update notifications — an attacker controlling the local
       filesystem can silently mask a compromised vendored dependency.
   * - SA-04
     - Patch Files (``.patch``)
     - Restricted
     - Unified-diff files referenced by ``patch:`` in the manifest.  Applied by
       ``patch-ng`` after fetch.  Risk: patch files carry no integrity hash in
       the manifest schema, so a tampered patch silently alters vendored code.
   * - SA-05
     - Local VCS Cache (temp)
     - Restricted
     - Temporary directory used during git-clone, svn-checkout, and archive
       extraction.  Deleted after content is copied to the destination.
       Path-traversal attacks are mitigated by ``check_no_path_traversal()`` and
       post-extraction symlink walks.
   * - SA-06
     - GitHub Actions Workflows
     - Restricted
     - ``.github/workflows/*.yml`` — 11 CI/CD pipeline definitions checked into
       the repository.  A malicious pull request modifying workflows can
       exfiltrate secrets or publish a backdoored release.  Mitigated by
       SHA-pinned actions and ``persist-credentials: false``.  Risk: ``secrets:
       inherit`` in ``ci.yml`` propagates all secrets to test and docs
       workflows triggered on pull requests.
   * - SA-07
     - PyPI OIDC Identity
     - Secret
     - GitHub OIDC token exchanged for a short-lived PyPI publish credential.
       No long-lived API token is stored — this is a significant security
       control.  The token is scoped to the GitHub Actions environment named
       ``pypi``.  Risk: misconfiguration of the OIDC issuer or the
       trusted-publisher mapping could allow an attacker to mint a valid publish
       token.
   * - SA-08
     - Audit / Check Reports
     - Restricted
     - SARIF, Jenkins warnings-ng, and Code Climate JSON produced by
       ``dfetch check``.  Also includes CodeQL and OpenSSF Scorecard results
       uploaded to GitHub Code Scanning.  Falsification hides vulnerabilities
       from downstream security dashboards.
   * - SA-09
     - dfetch Build / Dev Dependencies
     - Restricted
     - Python packages installed during CI (setuptools, build, pylint, bandit,
       mypy, pytest, etc.) and platform build tools (Ruby ``fpm``, Chocolatey
       packages).  Critical gap: installed via ``pip install .`` and
       ``pip install --upgrade pip build`` without ``--require-hashes``.  A
       compromised PyPI mirror or BGP hijack can substitute malicious build
       tools — a first-order supply-chain risk for dfetch's own release pipeline.
   * - SA-10
     - OpenSSF Scorecard Results
     - Restricted
     - Weekly OSSF Scorecard SARIF results uploaded to GitHub Code Scanning.
       Covers branch protection, CI tests, code review, maintained status,
       packaging, pinned dependencies, SAST, signed releases, token permissions,
       vulnerabilities, dangerous workflows, binary artifacts, fuzzing, licence,
       CII best practices, security policy, and webhooks.  Suppression or
       forgery hides supply-chain regressions.

Environmental Assets
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 8 28 14 50

   * - ID
     - Name
     - Classification
     - Description
   * - EA-01
     - Remote VCS Servers
     - Public
     - Upstream Git and SVN hosts: GitHub, GitLab, Gitea, self-hosted.  Not
       controlled by the dfetch project.
       **SSH transports**: ``BatchMode=yes`` and SSH host-key verification
       prevent credential prompts and protect against host impersonation.
       **Non-TLS transports** (plain ``http://`` or ``svn://``): these controls
       do not apply — a network-positioned attacker can intercept or substitute
       content without detection.  Use HTTPS, ``svn+https://``, or an SSH
       tunnel for all VCS remotes; dfetch does not enforce this in the manifest
       schema.
   * - EA-02
     - Archive HTTP Servers
     - Public
     - HTTP/HTTPS origins for ``.tar.gz``, ``.tgz``, ``.tar.bz2``, ``.tar.xz``,
       and ``.zip`` dependencies.  The ``integrity.hash`` field is the sole trust
       anchor; plain ``http://`` URLs are accepted without enforcement.
   * - EA-03
     - GitHub Repository
     - Restricted
     - Source code, pull requests, releases, and workflow definitions.  The
       repository's branch-protection and code-review policies are the primary
       defence against malicious contributions.
   * - EA-04
     - GitHub Actions Infrastructure
     - Restricted
     - Microsoft-operated ephemeral runners.  All third-party actions are pinned
       by commit SHA to limit supply-chain risk.
   * - EA-05
     - PyPI / TestPyPI
     - Public
     - Python Package Index and its staging registry.  Account takeover or
       registry compromise would affect every user who installs dfetch.
   * - EA-06
     - Developer Workstation / CI Runner
     - Restricted
     - Invokes dfetch.  Trusted at call time; a compromised CI runner is a pivot
       point for secret exfiltration.
   * - EA-07
     - Consumer Build System
     - Restricted
     - Compiles fetched source code (PA-02).  Not controlled by dfetch — it
       receives untrusted third-party source.
   * - EA-08
     - Network Transport
     - Public
     - HTTPS, SSH, SVN, and plain HTTP carrying all remote fetch traffic.  TLS
       enforcement is the responsibility of the OS and VCS clients.  Classified
       Public because the transport channel itself is shared infrastructure with
       no inherent confidentiality — confidentiality of the data it carries is
       the responsibility of the higher-layer protocols (TLS/SSH).


Data Flows
----------

The following data flows are defined in ``security/threat_model.py`` and annotated
with the security controls that are currently implemented.

.. list-table::
   :header-rows: 1
   :widths: 8 30 14 48

   * - ID
     - Flow
     - Protocol
     - Notes
   * - DF-01
     - Developer → dfetch CLI
     - (local)
     - CLI invocation: update / check / diff / report / add etc.
   * - DF-02
     - Manifest → dfetch CLI
     - (local)
     - StrictYAML parse; ``SAFE_STR`` regex rejects control characters.
   * - DF-03a
     - dfetch CLI → Remote VCS Server (HTTPS/SSH)
     - HTTPS / SSH
     - ``git fetch``, ``git ls-remote``, ``svn ls`` over encrypted transport.
       ``BatchMode=yes`` and ``GIT_TERMINAL_PROMPT=0`` suppress prompts; SSH
       host-key verification prevents impersonation.
   * - DF-03b
     - dfetch CLI → Remote VCS Server (svn:// / http://)
     - http / svn
     - Same commands over unencrypted transports accepted by dfetch.
       **No TLS, no host verification** — a MITM can substitute repository
       content or intercept credentials.  Manifest schema does not enforce
       HTTPS.  Mitigate by using HTTPS or ``svn+https://`` instead.
   * - DF-04a
     - Remote VCS Server → dfetch CLI (HTTPS/SSH)
     - HTTPS / SSH
     - Repository content over encrypted transport.  No end-to-end content
       hash — authenticity relies on transport security and upstream integrity.
   * - DF-04b
     - Remote VCS Server → dfetch CLI (svn:// / http://)
     - http / svn
     - Repository content over unencrypted transport.  An attacker can
       substitute arbitrary content without detection — no encryption and no
       content hash.
   * - DF-05
     - dfetch CLI → Archive HTTP Server
     - HTTP or HTTPS
     - HTTP GET to archive URL; follows up to 10 redirects.  Risk: plain
       ``http://`` URLs are accepted — traffic is unencrypted.
   * - DF-06
     - Archive HTTP Server → dfetch CLI
     - HTTP or HTTPS
     - Raw archive bytes streamed into dfetch.  Hash computed in-flight when
       ``integrity.hash`` is specified.  Critical: when the field is absent,
       no content verification occurs.
   * - DF-07
     - dfetch CLI → Vendor Directory
     - (local)
     - Post-validation copy to ``dst`` path.  Path-traversal checked via
       ``check_no_path_traversal()``; symlinks validated post-extraction.
   * - DF-08
     - dfetch CLI → Dependency Metadata
     - (local)
     - Writes ``.dfetch_data.yaml`` tracking remote URL, revision, and hash.
   * - DF-09
     - dfetch CLI → SBOM Output
     - (local)
     - CycloneDX BOM generation from metadata store contents.
   * - DF-10
     - Patch Files → dfetch CLI
     - (local)
     - ``patch-ng`` reads unified-diff file and applies to vendor directory.
       Risk: patch files carry no integrity hash; ``patch-ng`` path safety
       depends on its own internal implementation.
   * - DF-11
     - Contributor → GitHub Repository
     - HTTPS
     - External contributor opens a pull request.  Risk: ``secrets: inherit``
       in ``ci.yml`` propagates secrets to test and docs workflows triggered
       on PR — a malicious workflow step could exfiltrate secrets.
   * - DF-12
     - GitHub Actions Runner → GitHub Repository
     - HTTPS
     - CI checkout and build.  ``persist-credentials: false`` on all checkout
       steps; all third-party actions pinned by commit SHA.
   * - DF-13
     - GitHub Actions Runner → PyPI
     - HTTPS
     - On release event: wheel/sdist published via OIDC trusted publishing.
       Missing: no SLSA provenance attestation or Sigstore package signing.
   * - DF-14
     - Consumer → PyPI
     - HTTPS
     - ``pip install dfetch`` from PyPI.
   * - DF-15
     - PyPI Package → Consumer Build System
     - (installed)
     - Installed dfetch wheel executed in consumer environment.  Consumer
       cannot verify build provenance without SLSA attestation.


Implemented Security Controls
-------------------------------

The following controls are already in place and are reflected in the
``controls.*`` annotations on each pytm element.

.. list-table::
   :header-rows: 1
   :widths: 32 20 48

   * - Control
     - Asset(s) protected
     - Implementation
   * - Path-traversal prevention
     - PA-02, SA-05
     - ``check_no_path_traversal()`` resolves both the candidate path and the
       destination root via ``os.path.realpath`` (symlink-aware, not
       ``pathlib.Path.resolve``), then rejects any path whose resolved prefix
       does not start with the resolved root.  Applied to every file copy and
       post-extraction symlink.
       ``dfetch/util/util.py`` — ``check_no_path_traversal`` at line 277
   * - Decompression-bomb protection
     - SA-05, PA-02
     - Archives are rejected if uncompressed size exceeds 500 MB or the member
       count exceeds 10 000.
       ``dfetch/vcs/archive.py``
   * - Archive symlink validation
     - PA-02
     - Absolute and escaping (``..``) symlink targets are rejected for both TAR
       and ZIP.  A post-extraction walk validates all symlinks against the
       manifest root.
       ``dfetch/vcs/archive.py``
   * - Archive member type checks
     - PA-02, SA-05
     - TAR and ZIP members of type device file or FIFO are rejected outright.
       ``dfetch/vcs/archive.py``
   * - Integrity hash verification
     - PA-02, PA-03
     - SHA-256, SHA-384, and SHA-512 verified via ``hmac.compare_digest``
       (constant-time comparison, resistant to timing attacks).
       ``dfetch/vcs/integrity_hash.py``
   * - Non-interactive VCS
     - SA-02, EA-01
     - ``GIT_TERMINAL_PROMPT=0``, ``BatchMode=yes`` for Git;
       ``--non-interactive`` for SVN.  Credential prompts are suppressed to
       prevent interactive hijacking in CI.
       ``dfetch/vcs/git.py``, ``dfetch/vcs/svn.py``
   * - Subprocess safety
     - SA-01
     - All external commands invoked with ``shell=False`` and list-form
       arguments — no shell-injection vector.
       ``dfetch/util/cmdline.py``
   * - Manifest input validation
     - PA-01
     - StrictYAML schema with ``SAFE_STR = Regex(r"^[^\x00-\x1F\x7F-\x9F]*$")``
       rejects control characters in all string fields.
       ``dfetch/manifest/schema.py``
   * - Actions commit-SHA pinning
     - SA-06, EA-04
     - Every third-party GitHub Action is pinned to a full commit SHA (e.g.
       ``actions/checkout@de0fac2e...``), preventing tag-mutable supply-chain
       substitution.
       ``.github/workflows/*.yml``
   * - OIDC trusted publishing
     - SA-07, PA-04
     - PyPI publishes via ``pypa/gh-action-pypi-publish`` with ``id-token: write``
       and no stored long-lived API token.
       ``.github/workflows/python-publish.yml``
   * - Minimal workflow permissions
     - SA-06
     - Each workflow declares only the permissions it requires (default
       ``contents: read``).
       ``.github/workflows/*.yml``
   * - ``persist-credentials: false``
     - SA-02, EA-03
     - All ``actions/checkout`` steps drop the GitHub token from the working
       tree after checkout.
       ``.github/workflows/*.yml``
   * - Harden-runner (egress audit)
     - SA-02, EA-04
     - ``step-security/harden-runner`` is used in every workflow to audit
       outbound network connections.  Note: policy is ``audit``, not ``block``.
       ``.github/workflows/*.yml``
   * - OpenSSF Scorecard
     - EA-03, SA-10
     - Weekly OSSF Scorecard analysis uploaded to GitHub Code Scanning covers
       the full set of OpenSSF Scorecard checks (see the
       `OpenSSF Scorecard project <https://github.com/ossf/scorecard>`_ for
       the authoritative list).
       ``.github/workflows/scorecard.yml``
   * - CodeQL static analysis
     - SA-01, SA-06
     - CodeQL scans the Python codebase for security vulnerabilities on every
       push and pull request.
       ``.github/workflows/codeql-analysis.yml``
   * - Dependency review
     - SA-09
     - ``actions/dependency-review-action`` checks for known vulnerabilities in
       newly added dependencies on every pull request.
       ``.github/workflows/dependency-review.yml``
   * - ``bandit`` security linter
     - SA-01
     - ``bandit -r dfetch`` runs in CI to detect common Python security issues.
       ``pyproject.toml``


Known Gaps and Residual Risks
------------------------------

The following gaps were identified during asset analysis.  They represent
areas where existing controls are absent or incomplete.

.. list-table::
   :header-rows: 1
   :widths: 32 68

   * - Gap
     - Description
   * - Optional integrity hash
     - ``integrity.hash`` in the manifest is optional.  Archive dependencies
       without it have no content-authenticity guarantee.  Plain ``http://``
       URLs receive no protection at all.
   * - No integrity mechanism for Git/SVN
     - Git and SVN dependencies carry no equivalent to ``integrity.hash``.
       Authenticity relies entirely on transport security (TLS or SSH).
       Mutable references (branch, tag) can silently fetch different content
       after an upstream force-push.
   * - No patch-file integrity
     - Patch files referenced in the manifest carry no integrity hash.  A
       tampered patch can write to arbitrary paths through ``patch-ng``.
   * - No SLSA provenance
     - The release pipeline does not generate SLSA provenance attestations or
       Sigstore/cosign signatures for the published wheel.  Consumers cannot
       verify build provenance.
   * - No dfetch-self SBOM on PyPI
     - The CycloneDX SBOM generated by ``dfetch report`` covers vendored
       dependencies only.  dfetch itself has no machine-readable SBOM published
       alongside its PyPI release, as CRA Article 13 requires.
   * - Build deps without hash pinning
     - ``pip install .`` and ``pip install --upgrade pip build`` in CI do not
       use ``--require-hashes``.  A compromised PyPI mirror can substitute
       malicious build tooling.
   * - ``secrets: inherit`` scope
     - ``ci.yml`` passes all repository secrets to the test and docs workflows
       via ``secrets: inherit``.  A malicious pull request step in either
       workflow could exfiltrate secrets.
   * - Harden-runner in audit mode
     - ``step-security/harden-runner`` is configured with ``egress-policy:
       audit``.  Outbound connections are logged but not blocked — secret
       exfiltration via a compromised CI step is possible.
