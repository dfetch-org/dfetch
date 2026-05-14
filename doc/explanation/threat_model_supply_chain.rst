.. ============================================================
.. Auto-generated file — do not edit manually.
.. Regenerate with (see security/README.md for exact commands):
..
..   python -m security.tm_<supply_chain|usage> \
..       --report security/report_template.rst \
..       > doc/explanation/threat_model_<name>.rst
.. ============================================================

System Description
------------------

Threat model for dfetch.  Covers the pre-install lifecycle: code contribution, CI/CD, build (wheel / sdist), PyPI distribution, and consumer installation.  The installed dfetch package is the handoff point to tm_usage.py.

Assumptions
-----------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Name
     - Description

   * - Trusted workstation
     - Developer workstations are trusted at development and commit time.  A compromised workstation is outside the scope of this model.

   * - CI runner posture
     - GitHub Actions environments inherit the security posture of the GitHub-hosted runner.  Ephemeral runner isolation is provided by GitHub.

   * - Harden-runner in block mode
     - The ``harden-runner`` egress policy is set to ``block`` with an allowlist of permitted endpoints.  Outbound network connections from CI runners are blocked unless explicitly permitted.

   * - Build deps without hash pinning
     - dfetch's own build and dev dependencies are installed without ``--require-hashes``, so a compromised PyPI mirror can substitute malicious build tools.

   * - Attacker: Network-adjacent
     - Positioned on the same network segment as a CI runner or developer workstation - shared cloud tenant, BGP hijack, compromised DNS resolver, or corporate proxy.  Can intercept and modify unencrypted traffic (http://, svn://) and inject HTTP redirects.  Cannot break correctly implemented TLS or SSH.

   * - Attacker: Compromised upstream
     - A dependency maintainer account taken over via phishing, credential stuffing, or MFA bypass - or a maintainer acting maliciously.  Delivers attacker-controlled content over an authenticated channel; transport security provides no protection.  Mitigated only by commit-SHA pinning and human review before accepting any update.

   * - Attacker: Compromised registry or CDN
     - Holds write access to a public package registry (PyPI) or an archive CDN node, or is BGP-adjacent to one.  Serves malicious content under a valid TLS certificate - transport integrity does not detect server-side substitution.  Only cryptographic content hashes or signed attestations provide a defence.

   * - Attacker: Local filesystem
     - Holds write access to the developer workstation or CI runner working tree - gained via a compromised dev dependency, malicious post-install hook, or lateral movement.  Can tamper with ``.dfetch_data.yaml``, patch files, and vendored source after dfetch writes them to disk.

   * - Attacker: Malicious manifest contributor
     - A repository contributor who introduces a malicious ``dfetch.yaml`` change: redirecting a dep to an attacker-controlled URL, pointing ``dst:`` at a sensitive path, or embedding a credential-bearing URL.  dfetch is not the control point for this threat; code review is the intended mitigating boundary.


Dataflows
---------

.. list-table::
   :header-rows: 1
   :widths: 35 20 20 25

   * - Name
     - From
     - To
     - Protocol

   * - DF-11: Submit pull request
     - Contributor / Attacker
     - A-01: GitHub Repository
     - HTTPS

   * - DF-14: pip install dfetch
     - Consumer / End User
     - A-03: PyPI / TestPyPI
     - HTTPS

   * - DF-12: CI checkout and build
     - A-01: GitHub Repository
     - A-02: GitHub Actions Infrastructure
     -

   * - DF-13: Publish to PyPI (OIDC)
     - A-02: GitHub Actions Infrastructure
     - A-03: PyPI / TestPyPI
     - HTTPS

   * - DF-18: CI cache write
     - A-02: GitHub Actions Infrastructure
     - A-08b: GitHub Actions Build Cache
     - HTTPS

   * - DF-19: CI cache restore
     - A-08b: GitHub Actions Build Cache
     - A-02: GitHub Actions Infrastructure
     - HTTPS

   * - DF-17: CI write-back (SARIF / artifacts / cache)
     - A-02: GitHub Actions Infrastructure
     - A-01: GitHub Repository
     - HTTPS


Data Dictionary
---------------

.. list-table::
   :header-rows: 1
   :widths: 25 55 20

   * - Name
     - Description
     - Classification

   * - A-05: PyPI OIDC Identity
     - GitHub OIDC token exchanged for a short-lived PyPI publish credential.  No long-lived API token stored.  The token is scoped to the GitHub Actions environment named ``pypi``.  Risk: if the OIDC issuer or the PyPI trusted-publisher mapping is misconfigured, an attacker could mint a valid publish token.
     - SECRET


Actors
------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Name
     - Description

   * - Developer
     - dfetch project contributor: writes code, reviews PRs, cuts releases.  Trusted at workstation time; responsible for correct branch-protection and release workflow configuration.

   * - Contributor / Attacker
     - External contributor submitting pull requests, or an adversary attempting supply-chain manipulation (malicious PR, action-poisoning, or MITM on CI network traffic).  Code review, branch protection, and SHA-pinned Actions are the primary controls at this boundary.

   * - Consumer / End User
     - Installs dfetch from PyPI (``pip install dfetch``) or from binary installer, then invokes it on a developer workstation or in a CI pipeline.  Can verify four complementary attestation types using ``gh attestation verify`` as documented in the release-integrity guide (see C-026, C-039, C-040): SBOM attestation on the PyPI wheel; SBOM, SLSA build provenance, and VSA on binary installers; SLSA build provenance and in-toto test result attestation on the source archive.


Boundaries
----------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Name
     - Description

   * - Local Developer Environment
     - Developer workstation or local CI runner.  Assumed trusted at invocation time.  Hosts the manifest (``dfetch.yaml``), vendor directory, dependency metadata (``.dfetch_data.yaml``), and patch files.

   * - GitHub Actions Infrastructure
     - Microsoft-operated ephemeral runners executing the CI/CD workflows.  Egress traffic is blocked (``harden-runner`` with ``egress-policy: block``) with an allowlist of permitted endpoints; ``ci.yml`` forwards only explicitly named secrets to child workflows (``CODACY_PROJECT_TOKEN`` to ``test.yml``, ``GH_DFETCH_ORG_DEPLOY`` to ``docs.yml``).

   * - PyPI / TestPyPI
     - Python Package Index and its staging registry.  dfetch publishes via OIDC trusted publishing - no long-lived API token stored.

   * - Internet
     - Public internet - upstream package registries, PyPI, GitHub, CDN nodes, and other external endpoints reachable by the CI/CD infrastructure.


Assets
------

.. list-table::
   :header-rows: 1
   :widths: 25 55 20

   * - Name
     - Description
     - Type

   * - A-01: GitHub Repository
     - Source code, PRs, releases, and workflow definitions.  GitHub Actions workflows (``.github/workflows/``) with ``contents:write`` permission can modify repository state and trigger releases.
     - ExternalEntity

   * - A-02: GitHub Actions Infrastructure
     - Microsoft-operated ephemeral runner executing CI/CD workflows.  Egress policy is ``block`` with an explicit allowlist of permitted endpoints - non-allowlisted outbound connections are blocked at the kernel level by ``step-security/harden-runner``.
     - ExternalEntity

   * - A-03: PyPI / TestPyPI
     - Python Package Index.  dfetch is published via OIDC trusted publishing (no long-lived API token).  Account takeover or registry compromise would affect every consumer installing dfetch.
     - ExternalEntity

   * - Release Gate / Code Review
     - Branch-protection rules and mandatory peer code review enforced before merging to the default branch.  Controls privileged operations: PR merge, direct push to main, and release-workflow trigger.  A compromised maintainer account with merge rights bypasses peer review and can trigger a malicious release without any automated block.  No hardware-token MFA or mandatory second-maintainer approval for release operations is currently enforced.
     - Process

   * - GitHub Actions Workflow
     - CI/CD pipelines: test, build (wheel/msi/deb/rpm), lint, CodeQL, Scorecard, dependency-review, docs, release.  All actions pinned by commit SHA.  harden-runner used in every workflow that executes steps on a runner (egress: block with endpoint allowlist); ci.yml is a dispatcher-only workflow with no runner steps and does not include harden-runner.
     - Process

   * - Python Build (wheel / sdist)
     - Runs ``python -m build`` to produce wheel and sdist.  Build deps (setuptools, build, fpm, gem) fetched from PyPI/RubyGems without hash pinning.  SLSA provenance attestations are generated by the release workflow.
     - Process

   * - A-04: dfetch PyPI Package
     - Published wheel and sdist on PyPI (https://pypi.org/project/dfetch/).  Published via OIDC trusted publishing - no long-lived API token stored.  A machine-readable CycloneDX SBOM is generated during the build and published alongside the release.  Compromise of the PyPI account or registry affects every consumer.
     - Datastore

   * - A-06: OpenSSF Scorecard Results
     - Weekly OSSF Scorecard SARIF results uploaded to GitHub Code Scanning.  Covers: branch-protection, CI-tests, code-review, maintained, packaging, pinned-dependencies, SAST, signed-releases, token-permissions, vulnerabilities, dangerous-workflow, binary-artifacts, fuzzing, license, CII-best-practices, security-policy, webhooks.  Suppression or forgery hides supply-chain regressions.
     - Datastore

   * - A-07: dfetch Build / Dev Dependencies
     - Python packages installed during CI: setuptools, build, pylint, bandit, mypy, pytest, etc.  Ruby gem ``fpm`` for platform builds.  Installed via ``pip install .`` and ``pip install --upgrade pip build`` without ``--require-hashes`` - a compromised PyPI mirror or BGP hijack can substitute malicious build tools.  ``gem install fpm`` and ``choco install svn/zig`` are also not hash-verified.
     - Datastore

   * - A-08: GitHub Actions Workflows
     - ``.github/workflows/*.yml`` - CI/CD configuration checked into the repository.  11 workflows: ci, build, run, test, docs, release, python-publish, dependency-review, codeql-analysis, scorecard, devcontainer.  A malicious PR that modifies workflows can exfiltrate secrets or publish a backdoored release.  Mitigated by: SHA-pinned actions, persist-credentials:false, minimal permissions.
     - Datastore

   * - A-08b: GitHub Actions Build Cache
     - GitHub Actions cache entries written and restored across pipeline runs.  Used to speed up dependency installation (pip, gem) and incremental builds.  Cache-poisoning from forked PRs (DFT-28, SLSA E6: poison the build cache) is mitigated by ref-scoped cache keys: build.yml includes ``${{ github.ref_name }}`` in both ``key`` and ``restore-keys`` (C-033), which isolates PR and release caches per branch so a fork cannot write into the release cache namespace.
     - Datastore





Controls
--------

.. list-table::
   :header-rows: 1
   :widths: 8 20 8 14 15 35

   * - ID
     - Name
     - Risk
     - STRIDE
     - Threats
     - Description
   * - C-009
     - Actions commit-SHA pinning
     - High
     - Tampering
     - DFT-07
     - Mitigates: Every third-party GitHub Action is pinned to a full commit SHA, preventing tag-mutable supply-chain substitution.  ``.github/workflows/*.yml``
   * - C-010
     - OIDC trusted publishing
     - High
     - Spoofing, Elevation of Privilege
     - DFT-07
     - Mitigates: PyPI publishes via ``pypa/gh-action-pypi-publish`` with ``id-token: write`` and no stored long-lived API token.  ``.github/workflows/python-publish.yml``
   * - C-011
     - Minimal workflow permissions
     - Medium
     - Elevation of Privilege
     - DFT-07
     - Mitigates: Each workflow declares only the permissions it requires (default ``contents: read``).  ``.github/workflows/*.yml``
   * - C-012
     - persist-credentials: false
     - Medium
     - Information Disclosure
     - DFT-07
     - Mitigates: ``persist-credentials: false`` is set on all checkout steps across all workflows that run on a runner.  The GitHub token is not persisted in the working tree after checkout.  ``.github/workflows/*.yml``
   * - C-013
     - Harden-runner (egress block)
     - High
     - Information Disclosure, Tampering
     - DFT-07, DFT-29
     - Mitigates: ``step-security/harden-runner`` is used in every workflow with ``egress-policy: block`` and an allowlist of permitted endpoints.  All non-allowlisted outbound connections are blocked.  ``.github/workflows/*.yml``
   * - C-014
     - OpenSSF Scorecard
     - Low
     - Tampering
     - DFT-07, DFT-10
     - Mitigates: Weekly OSSF Scorecard analysis uploaded to GitHub Code Scanning covers the full set of OpenSSF Scorecard checks.  ``.github/workflows/scorecard.yml``
   * - C-015
     - CodeQL static analysis
     - Medium
     - Tampering, Elevation of Privilege
     - DFT-03, DFT-06
     - Mitigates: CodeQL scans the Python codebase for security vulnerabilities on pushes and pull requests targeting ``main``, and on a weekly cron schedule.  ``.github/workflows/codeql-analysis.yml``
   * - C-016
     - Dependency review
     - Medium
     - Tampering
     - DFT-10
     - Mitigates: ``actions/dependency-review-action`` checks for known vulnerabilities in newly added dependencies on every pull request.  ``.github/workflows/dependency-review.yml``
   * - C-017
     - bandit security linter
     - Low
     - Tampering, Elevation of Privilege
     - DFT-03, DFT-06
     - Mitigates: ``bandit -r dfetch`` runs in CI to detect common Python security issues.  ``pyproject.toml``
   * - C-021
     - Sigstore SBOM attestation
     - Medium
     - Spoofing, Tampering
     - DFT-05
     - Mitigates: The release pipeline generates CycloneDX SBOM attestations via ``actions/attest`` with Sigstore signatures.  These attest the software composition (SBOM) of the published packages using predicate type ``https://cyclonedx.org/bom``.
   * - C-022
     - CycloneDX SBOM on PyPI
     - Low
     - Repudiation
     - DFT-02
     - Mitigates: A CycloneDX SBOM is generated during the build and published alongside the PyPI release, satisfying CRA Article 13 requirements.
   * - C-024
     - ``secrets: inherit`` scope
     - Medium
     - Information Disclosure
     - DFT-07
     - Mitigates: ``ci.yml`` only passes required repository secrets to the test and docs workflows, preventing malicious PR steps from exfiltrating unrelated secrets.
   * - C-026
     - Consumer-side package provenance verification
     - Medium
     - Spoofing, Tampering
     - DFT-17, DFT-25
     - Mitigates: Consumers installing dfetch via ``pip install dfetch`` have access to documented procedures to verify the SBOM (CycloneDX) attestation of the PyPI wheel using the GitHub CLI (``gh attestation verify``).  Consumers installing binary packages (deb, rpm, pkg, msi) can verify SLSA build provenance, SBOM, and VSA attestations.  Consumers working from source can verify SLSA build provenance and in-toto test result attestations on the source archive.  Platform-specific instructions for Linux, macOS, and Windows are provided in ``doc/howto/verify-integrity.rst``.  This is an interim mitigation pending PEP 740 built-in support in pip.  Without this documentation, a compromised PyPI account, namespace-squatting, or dependency-confusion could serve malicious code undetected (DFT-17).  An attacker controlling the release pipeline could publish a plausible attestation alongside a backdoored wheel (DFT-25).  By providing clear, copy-paste instructions, we enable security-conscious consumers to verify provenance before installation.  ``doc/tutorials/installation.rst#verifying-release-integrity``
   * - C-032
     - Consumer attestation verification pins to release tag ref
     - Medium
     - Tampering, Spoofing
     - DFT-27
     - Mitigates: All ``gh attestation verify`` commands in the installation guide use ``--cert-identity`` pinned to the release workflow at a specific version tag (e.g. ``...python-publish.yml@refs/tags/v<version>`` for pip packages, ``...build.yml@refs/tags/v<version>`` for binary installers) combined with ``--cert-oidc-issuer https://token.actions.githubusercontent.com``.  This rejects attestations produced by any workflow or branch other than the expected release workflow on an official version tag.  A build from an unofficial fork or unprotected branch would produce an attestation with a different cert-identity and fail verification.  ``doc/tutorials/installation.rst``
   * - C-033
     - Ref-scoped build cache keys isolate PR and release builds
     - High
     - Tampering
     - DFT-28
     - Mitigates: ccache and clcache keys in ``build.yml`` include ``${{ github.ref_name }}`` so cache entries written by a pull-request build are scoped to the PR's branch name and cannot be restored by a release-tag build.  A malicious fork PR step cannot pre-populate a cache slot that the release workflow will restore, because the release tag name is not reachable from the PR's branch ref.  ``.github/workflows/build.yml``
   * - C-038
     - Ancestry enforcement on dfetch main branch
     - Low
     - Tampering
     - DFT-33
     - Mitigates: GitHub branch-protection rules on the dfetch ``main`` branch prohibit force-pushes, satisfying the SLSA Source Level 2 ancestry-enforcement requirement.  The immutable revision lineage of the main branch is preserved: no contributor can rewrite history and orphan a previously-audited commit SHA.  Consumers who pin to a dfetch commit SHA can rely on that SHA remaining reachable indefinitely.  ``.github/workflows/``
   * - C-039
     - Source build provenance and VSA attestations
     - High
     - Spoofing, Tampering, Repudiation
     - DFT-31, DFT-25
     - Mitigates: Every dfetch release ships two complementary Sigstore-signed attestations that together let consumers trace the full source → binary chain.  SLSA build provenance (``source-provenance.yml``) on the source archive proves the archive was produced from the official tagged commit by the official CI workflow, recording the exact inputs used at build time.  A Verification Summary Attestation (VSA, ``build.yml``) on binary installers records that the source archive was itself attested and verified before the binary was produced, linking source-level trust to the installed package.  Both are signed by GitHub Actions via Sigstore and can be verified using ``gh attestation verify`` with ``--predicate-type https://slsa.dev/provenance/v1`` or ``--predicate-type https://slsa.dev/verification_summary/v1`` respectively.  This substantially mitigates DFT-31 (consumers now have attestations to verify against) and DFT-25 (forged provenance would fail Sigstore verification).  The remaining gap (no formal SLSA Source Level attestation of governance controls) is tracked in C-037.  ``doc/howto/verify-integrity.rst``
   * - C-040
     - Test result attestation on source archive
     - Medium
     - Repudiation, Tampering
     - DFT-31
     - Mitigates: The CI test workflow (``test.yml``) generates an in-toto test result attestation (predicate type ``https://in-toto.io/attestation/test-result/v0.1``) for every release and main-branch commit.  The attestation proves the full CI test suite ran against the exact source archive and every check passed, before any binary was produced from that source.  Consumers can verify it using ``gh attestation verify dfetch-source.tar.gz`` with ``--predicate-type https://in-toto.io/attestation/test-result/v0.1`` and ``--cert-identity`` pinned to ``test.yml`` at the release tag ref.  This provides an additional layer of assurance beyond build provenance: not only was the artifact produced from the official commit, but the test suite demonstrably passed on that exact source before any binary was built.  ``.github/workflows/test.yml``


Gaps
----

.. list-table::
   :header-rows: 1
   :widths: 8 20 8 14 15 35

   * - ID
     - Name
     - Risk
     - STRIDE
     - Threats
     - Description
   * - C-023
     - Build deps without hash pinning
     - High
     - Tampering
     - DFT-10
     - Affects: ``pip install .`` and ``pip install --upgrade pip build`` in CI do not use ``--require-hashes``.  A compromised PyPI mirror can substitute malicious build tooling.
   * - C-037
     - No formal SLSA Source Level attestation of repository governance controls
     - Low
     - Repudiation, Spoofing
     - DFT-31
     - Affects: dfetch now publishes SLSA build provenance for source archives, VSAs for binary installers (C-039), and in-toto test result attestations (C-040).  These close the 'no attestation to verify against' concern: consumers can cryptographically verify the artifact chain.  The remaining, narrower gap is that dfetch does not publish formal SLSA Source Provenance Attestations generated by a SLSA Source Generator — attestations that would prove the specific source-level governance controls applied on each commit (branch protection, mandatory code review, ancestry enforcement).  C-038 establishes that ancestry enforcement is in place and C-026 documents what consumers can verify; the gap is in machine-readable, verifiable proof of those governance controls rather than the controls themselves.  Risk is Low: the missing piece is a formal SLSA Source Level certificate (per the SLSA Source Track spec) rather than the absence of any assurance.  Fix: publish Source Provenance Attestations via ``slsa-framework/slsa-source-corroborator`` or equivalent on each push to main.
   * - C-025
     - No hardware-token MFA for release operations
     - High
     - Spoofing, Elevation of Privilege
     - DFT-11
     - Affects: No hardware-token (FIDO2/WebAuthn) MFA or mandatory second-approver sign-off is required for accounts with merge or release-trigger rights.  A compromised maintainer account - via phishing, credential stuffing, or SMS-TOTP bypass - can merge a backdoored PR and trigger the release workflow without any automated block.  Enforce FIDO2 MFA on all accounts with merge rights and add a required reviewer to the ``pypi`` deployment environment.
