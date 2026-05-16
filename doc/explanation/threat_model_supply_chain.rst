dfetch Supply Chain
===================

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


.. raw:: html

   <div class="tm-diagram" title="Click to view fullscreen">

Data Flow Diagram
-----------------

.. uml::

   @startdot
   digraph tm {
       graph [
           fontname = Arial;
           fontsize = 14;
       ]
       node [
           fontname = Arial;
           fontsize = 14;
           rankdir = lr;
       ]
       edge [
           shape = none;
           arrowtail = onormal;
           fontname = Arial;
           fontsize = 12;
       ]
       labelloc = "t";
       fontsize = 20;
       nodesep = 1;

       subgraph cluster_boundary_ConsumerEnvironment_88f2d9c06f {
           graph [
               fontsize = 10;
               fontcolor = black;
               style = dashed;
               color = firebrick2;
               label = <<i>Consumer\nEnvironment</i>>;
           ]

           actor_ConsumerEndUser_f8af758679 [
               shape = square;
               color = black;
               fontcolor = black;
               label = "Consumer / End\nUser";
               margin = 0.02;
           ]

       }

       subgraph cluster_boundary_GitHubPlatform_579e9aae81 {
           graph [
               fontsize = 10;
               fontcolor = black;
               style = dashed;
               color = firebrick2;
               label = <<i>GitHub Platform</i>>;
           ]

           externalentity_AGitHubRepositorymainprotected_2c440ebe53 [
               shape = square;
               color = black;
               fontcolor = black;
               label = "A-01: GitHub\nRepository (main /\nprotected)";
               margin = 0.02;
           ]

           externalentity_AbGitHubRepositoryfeaturebranchesPRs_0291419f72 [
               shape = square;
               color = black;
               fontcolor = black;
               label = "A-01b: GitHub\nRepository\n(feature branches\n/ PRs)";
               margin = 0.02;
           ]

           externalentity_AGitHubActionsInfrastructure_c76a0a7067 [
               shape = square;
               color = black;
               fontcolor = black;
               label = "A-02: GitHub\nActions\nInfrastructure";
               margin = 0.02;
           ]

           process_ReleaseGateCodeReview_9345ab4c19 [
               shape = circle;
               color = black;
               fontcolor = black;
               label = "Release Gate /\nCode Review";
               margin = 0.02;
           ]

           process_GitHubActionsWorkflow_86e4604564 [
               shape = circle;
               color = black;
               fontcolor = black;
               label = "GitHub Actions\nWorkflow";
               margin = 0.02;
           ]

           process_PythonBuildwheelsdist_b2e5892d06 [
               shape = circle;
               color = black;
               fontcolor = black;
               label = "Python Build\n(wheel / sdist)";
               margin = 0.02;
           ]

           datastore_AdfetchBuildDevDependencies_990b886585 [
               shape = cylinder;
               color = black;
               fontcolor = black;
               label = "A-07: dfetch Build\n/ Dev Dependencies";
           ]

           datastore_AbGitHubActionsBuildCache_9df04f8dae [
               shape = cylinder;
               color = black;
               fontcolor = black;
               label = "A-08b: GitHub\nActions Build\nCache";
           ]

       }

       subgraph cluster_boundary_LocalDeveloperEnvironment_acf3059e70 {
           graph [
               fontsize = 10;
               fontcolor = black;
               style = dashed;
               color = firebrick2;
               label = <<i>Local Developer\nEnvironment</i>>;
           ]

           actor_DeveloperContributor_d2006ce1bb [
               shape = square;
               color = black;
               fontcolor = black;
               label = "Developer /\nContributor";
               margin = 0.02;
           ]

       }

       subgraph cluster_boundary_PyPITestPyPI_f2eb7a3ff7 {
           graph [
               fontsize = 10;
               fontcolor = black;
               style = dashed;
               color = firebrick2;
               label = <<i>PyPI / TestPyPI</i>>;
           ]

           externalentity_APyPITestPyPI_c6f87088c2 [
               shape = square;
               color = black;
               fontcolor = black;
               label = "A-03: PyPI /\nTestPyPI";
               margin = 0.02;
           ]

       }

       actor_DeveloperContributor_d2006ce1bb -> externalentity_AbGitHubRepositoryfeaturebranchesPRs_0291419f72 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-11: Push\ncommits / open PR";
       ]

       externalentity_AbGitHubRepositoryfeaturebranchesPRs_0291419f72 -> process_ReleaseGateCodeReview_9345ab4c19 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-22: PR enters\ncode review";
       ]

       externalentity_AGitHubRepositorymainprotected_2c440ebe53 -> process_GitHubActionsWorkflow_86e4604564 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-12: Main branch\nworkflows drive CI\nexecution";
       ]

       externalentity_AbGitHubRepositoryfeaturebranchesPRs_0291419f72 -> externalentity_AGitHubActionsInfrastructure_c76a0a7067 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-13a: PR CI\ncheckout";
       ]

       externalentity_AGitHubRepositorymainprotected_2c440ebe53 -> externalentity_AGitHubActionsInfrastructure_c76a0a7067 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-13b: Release CI\ncheckout";
       ]

       datastore_AbGitHubActionsBuildCache_9df04f8dae -> externalentity_AGitHubActionsInfrastructure_c76a0a7067 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-14: CI cache\nrestore";
       ]

       process_GitHubActionsWorkflow_86e4604564 -> process_PythonBuildwheelsdist_b2e5892d06 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-15: Workflow\ntriggers build\nstep";
       ]

       process_PythonBuildwheelsdist_b2e5892d06 -> externalentity_AGitHubActionsInfrastructure_c76a0a7067 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-15b: Built\nwheel/sdist\nartifacts";
       ]

       externalentity_APyPITestPyPI_c6f87088c2 -> datastore_AdfetchBuildDevDependencies_990b886585 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-16: CI fetches\nbuild/dev deps\nfrom PyPI";
       ]

       datastore_AdfetchBuildDevDependencies_990b886585 -> process_PythonBuildwheelsdist_b2e5892d06 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-17: Build tools\nconsumed by build\nstep";
       ]

       externalentity_AGitHubActionsInfrastructure_c76a0a7067 -> datastore_AbGitHubActionsBuildCache_9df04f8dae [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-18: CI cache\nwrite";
       ]

       externalentity_AGitHubActionsInfrastructure_c76a0a7067 -> externalentity_AGitHubRepositorymainprotected_2c440ebe53 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-19: CI write-\nback (SARIF /\nartifacts)";
       ]

       process_ReleaseGateCodeReview_9345ab4c19 -> externalentity_AGitHubRepositorymainprotected_2c440ebe53 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-23: Approved\nmerge to main";
       ]

       externalentity_AGitHubActionsInfrastructure_c76a0a7067 -> externalentity_APyPITestPyPI_c6f87088c2 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-24: Publish\nwheel to PyPI\n(OIDC)";
       ]

       actor_ConsumerEndUser_f8af758679 -> externalentity_APyPITestPyPI_c6f87088c2 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-25: pip install\ndfetch";
       ]

       externalentity_APyPITestPyPI_c6f87088c2 -> actor_ConsumerEndUser_f8af758679 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-26: Consumer\ndownloads dfetch\nfrom PyPI";
       ]

   }
   @enddot

.. raw:: html

   </div>
   <style>
   .tm-diagram{cursor:zoom-in;}
   .tm-diagram:fullscreen,
   .tm-diagram:-webkit-full-screen{
     background:#fff;display:flex;
     align-items:center;justify-content:center;
   }
   .tm-diagram:fullscreen img,
   .tm-diagram:-webkit-full-screen img{
     max-width:100vw;max-height:100vh;
     width:auto;height:auto;cursor:zoom-out;
   }
   </style>
   <script>
   (function(){
     document.querySelectorAll('.tm-diagram:not([data-fs])').forEach(function(d){
       d.dataset.fs='1';
       d.addEventListener('click',function(){
         if(!document.fullscreenElement){
           (d.requestFullscreen||d.webkitRequestFullscreen).call(d);
         }else{
           (document.exitFullscreen||document.webkitExitFullscreen).call(document);
         }
       });
     });
   })();
   </script>

.. raw:: html

   <div class="tm-diagram" title="Click to view fullscreen">

Sequence Diagram
----------------

.. uml::

   @startuml
   skinparam defaultFontSize 16
   actor actor_DeveloperContributor_d2006ce1bb as "Developer /\nContributor"
   actor actor_ConsumerEndUser_f8af758679 as "Consumer /\nEnd User"
   entity externalentity_AGitHubRepositorymainprotected_2c440ebe53 as "A-01: GitHub\nRepository\n(main /\nprotected)"
   entity externalentity_AbGitHubRepositoryfeaturebranchesPRs_0291419f72 as "A-01b:\nGitHub\nRepository\n(feature\nbranches /\nPRs)"
   entity externalentity_AGitHubActionsInfrastructure_c76a0a7067 as "A-02: GitHub\nActions\nInfrastructure"
   entity externalentity_APyPITestPyPI_c6f87088c2 as "A-03: PyPI /\nTestPyPI"
   entity process_ReleaseGateCodeReview_9345ab4c19 as "Release Gate\n/ Code\nReview"
   entity process_GitHubActionsWorkflow_86e4604564 as "GitHub\nActions\nWorkflow"
   entity process_PythonBuildwheelsdist_b2e5892d06 as "Python Build\n(wheel /\nsdist)"
   database datastore_AdfetchBuildDevDependencies_990b886585 as "A-07: dfetch\nBuild / Dev\nDependencies"
   database datastore_AbGitHubActionsBuildCache_9df04f8dae as "A-08b:\nGitHub\nActions\nBuild Cache"

   actor_DeveloperContributor_d2006ce1bb -> externalentity_AbGitHubRepositoryfeaturebranchesPRs_0291419f72: DF-11: Push commits / open PR
   externalentity_AbGitHubRepositoryfeaturebranchesPRs_0291419f72 -> process_ReleaseGateCodeReview_9345ab4c19: DF-22: PR enters code review
   externalentity_AGitHubRepositorymainprotected_2c440ebe53 -> process_GitHubActionsWorkflow_86e4604564: DF-12: Main branch workflows drive CI execution
   externalentity_AbGitHubRepositoryfeaturebranchesPRs_0291419f72 -> externalentity_AGitHubActionsInfrastructure_c76a0a7067: DF-13a: PR CI checkout
   externalentity_AGitHubRepositorymainprotected_2c440ebe53 -> externalentity_AGitHubActionsInfrastructure_c76a0a7067: DF-13b: Release CI checkout
   datastore_AbGitHubActionsBuildCache_9df04f8dae -> externalentity_AGitHubActionsInfrastructure_c76a0a7067: DF-14: CI cache restore
   process_GitHubActionsWorkflow_86e4604564 -> process_PythonBuildwheelsdist_b2e5892d06: DF-15: Workflow triggers build step
   process_PythonBuildwheelsdist_b2e5892d06 -> externalentity_AGitHubActionsInfrastructure_c76a0a7067: DF-15b: Built wheel/sdist artifacts
   externalentity_APyPITestPyPI_c6f87088c2 -> datastore_AdfetchBuildDevDependencies_990b886585: DF-16: CI fetches build/dev deps from PyPI
   datastore_AdfetchBuildDevDependencies_990b886585 -> process_PythonBuildwheelsdist_b2e5892d06: DF-17: Build tools consumed by build step
   externalentity_AGitHubActionsInfrastructure_c76a0a7067 -> datastore_AbGitHubActionsBuildCache_9df04f8dae: DF-18: CI cache write
   externalentity_AGitHubActionsInfrastructure_c76a0a7067 -> externalentity_AGitHubRepositorymainprotected_2c440ebe53: DF-19: CI write-back (SARIF / artifacts)
   process_ReleaseGateCodeReview_9345ab4c19 -> externalentity_AGitHubRepositorymainprotected_2c440ebe53: DF-23: Approved merge to main
   externalentity_AGitHubActionsInfrastructure_c76a0a7067 -> externalentity_APyPITestPyPI_c6f87088c2: DF-24: Publish wheel to PyPI (OIDC)
   actor_ConsumerEndUser_f8af758679 -> externalentity_APyPITestPyPI_c6f87088c2: DF-25: pip install dfetch
   externalentity_APyPITestPyPI_c6f87088c2 -> actor_ConsumerEndUser_f8af758679: DF-26: Consumer downloads dfetch from PyPI
   @enduml

.. raw:: html

   </div>
   <style>
   .tm-diagram{cursor:zoom-in;}
   .tm-diagram:fullscreen,
   .tm-diagram:-webkit-full-screen{
     background:#fff;display:flex;
     align-items:center;justify-content:center;
   }
   .tm-diagram:fullscreen img,
   .tm-diagram:-webkit-full-screen img{
     max-width:100vw;max-height:100vh;
     width:auto;height:auto;cursor:zoom-out;
   }
   </style>
   <script>
   (function(){
     document.querySelectorAll('.tm-diagram:not([data-fs])').forEach(function(d){
       d.dataset.fs='1';
       d.addEventListener('click',function(){
         if(!document.fullscreenElement){
           (d.requestFullscreen||d.webkitRequestFullscreen).call(d);
         }else{
           (document.exitFullscreen||document.webkitExitFullscreen).call(document);
         }
       });
     });
   })();
   </script>

Dataflows
---------

.. list-table::
   :header-rows: 1
   :widths: 35 20 20 25

   * - Name
     - From
     - To
     - Protocol

   * - DF-11: Push commits / open PR
     - Developer / Contributor
     - A-01b: GitHub Repository (feature branches / PRs)
     - HTTPS

   * - DF-22: PR enters code review
     - A-01b: GitHub Repository (feature branches / PRs)
     - Release Gate / Code Review
     - 

   * - DF-12: Main branch workflows drive CI execution
     - A-01: GitHub Repository (main / protected)
     - GitHub Actions Workflow
     - 

   * - DF-13a: PR CI checkout
     - A-01b: GitHub Repository (feature branches / PRs)
     - A-02: GitHub Actions Infrastructure
     - 

   * - DF-13b: Release CI checkout
     - A-01: GitHub Repository (main / protected)
     - A-02: GitHub Actions Infrastructure
     - 

   * - DF-14: CI cache restore
     - A-08b: GitHub Actions Build Cache
     - A-02: GitHub Actions Infrastructure
     - HTTPS

   * - DF-15: Workflow triggers build step
     - GitHub Actions Workflow
     - Python Build (wheel / sdist)
     - 

   * - DF-15b: Built wheel/sdist artifacts
     - Python Build (wheel / sdist)
     - A-02: GitHub Actions Infrastructure
     - 

   * - DF-16: CI fetches build/dev deps from PyPI
     - A-03: PyPI / TestPyPI
     - A-07: dfetch Build / Dev Dependencies
     - HTTPS

   * - DF-17: Build tools consumed by build step
     - A-07: dfetch Build / Dev Dependencies
     - Python Build (wheel / sdist)
     - 

   * - DF-18: CI cache write
     - A-02: GitHub Actions Infrastructure
     - A-08b: GitHub Actions Build Cache
     - HTTPS

   * - DF-19: CI write-back (SARIF / artifacts)
     - A-02: GitHub Actions Infrastructure
     - A-01: GitHub Repository (main / protected)
     - HTTPS

   * - DF-23: Approved merge to main
     - Release Gate / Code Review
     - A-01: GitHub Repository (main / protected)
     - 

   * - DF-24: Publish wheel to PyPI (OIDC)
     - A-02: GitHub Actions Infrastructure
     - A-03: PyPI / TestPyPI
     - HTTPS

   * - DF-25: pip install dfetch
     - Consumer / End User
     - A-03: PyPI / TestPyPI
     - HTTPS

   * - DF-26: Consumer downloads dfetch from PyPI
     - A-03: PyPI / TestPyPI
     - Consumer / End User
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

   * - Developer / Contributor
     - Anyone who writes code for dfetch: core maintainers who push directly and cut releases, and external contributors who submit pull requests.  Maintainers are trusted at workstation time and are responsible for correct branch-protection and release workflow configuration.  External contributors are untrusted until their PR passes code review and CI.

   * - Consumer / End User
     - Installs dfetch from PyPI (``pip install dfetch``) or from binary installer, then invokes it on a developer workstation or in a CI pipeline.  Can verify five complementary attestation types using ``gh attestation verify`` as documented in the release-integrity guide (see C-026, C-037, C-039, C-040): SBOM attestation on the PyPI wheel; SBOM, SLSA build provenance, and VSA on binary installers; SLSA build provenance, in-toto test result attestation, and SLSA Source Provenance Attestation on the source archive and main-branch commits.


Boundaries
----------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Name
     - Description

   * - Local Developer Environment
     - Developer workstation or local CI runner.  Assumed trusted at invocation time.  Hosts the manifest (``dfetch.yaml``), vendor directory, dependency metadata (``.dfetch_data.yaml``), and patch files.

   * - Consumer Environment
     - End-user workstation or downstream CI pipeline where dfetch is installed and invoked.  Distinct from the developer environment: no source checkout, no signing keys, no deploy access.  The consumer is trusted at invocation time but has no special relationship with the dfetch release infrastructure.

   * - GitHub Platform
     - GitHub-hosted infrastructure: repository, CI/CD runners, Actions workflows, build cache, and code-scanning results.  Egress traffic on runners is blocked (``harden-runner`` with ``egress-policy: block``) with an allowlist of permitted endpoints; ``ci.yml`` forwards only explicitly named secrets to child workflows (``CODACY_PROJECT_TOKEN`` to ``test.yml``, ``GH_DFETCH_ORG_DEPLOY`` to ``docs.yml``).

   * - PyPI / TestPyPI
     - Python Package Index and its staging registry.  dfetch publishes via OIDC trusted publishing - no long-lived API token stored.


Assets
------

.. list-table::
   :header-rows: 1
   :widths: 25 55 20

   * - Name
     - Description
     - Type

   * - A-01: GitHub Repository (main / protected)
     - The protected ``main`` branch: force-push disabled, merges require passing CI and at least one approving review.  Contains the authoritative workflow definitions (``.github/workflows/``), release tags, and published release assets.  Workflow files on main are what GitHub Actions actually executes — a PR cannot override them for its own CI run.  ``contents:write`` permission allows CI to upload SARIF results and release assets.
     - ExternalEntity

   * - A-01b: GitHub Repository (feature branches / PRs)
     - Unprotected feature branches and fork PRs: no mandatory review, no CI-gate requirement to push.  Any authenticated GitHub user can open a PR modifying ``.github/workflows/`` files; those changes are reviewed before merging to main but execute with restricted permissions during CI (no access to production secrets).  A malicious PR modifying workflow files could attempt to exfiltrate secrets during the PR CI run, mitigated by ``ci.yml`` secret scoping (C-024) and harden-runner egress block (C-013).
     - ExternalEntity

   * - A-02: GitHub Actions Infrastructure
     - Microsoft-operated ephemeral runner executing CI/CD workflows.  Egress policy is ``block`` with an explicit allowlist of permitted endpoints - non-allowlisted outbound connections are blocked at the kernel level by ``step-security/harden-runner``.
     - ExternalEntity

   * - A-03: PyPI / TestPyPI
     - Python Package Index - both the registry service and the published dfetch wheel/sdist (https://pypi.org/project/dfetch/).  Published via OIDC trusted publishing; no long-lived API token stored.  A machine-readable CycloneDX SBOM is generated during the build and published alongside the release.  Account takeover, registry compromise, or namespace-squatting would affect every consumer installing dfetch.
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

   * - A-07: dfetch Build / Dev Dependencies
     - Python packages installed during CI: setuptools, build, pylint, bandit, mypy, pytest, etc.  Ruby gem ``fpm`` for platform builds.  Installed via ``pip install .`` and ``pip install --upgrade pip build`` without ``--require-hashes`` - a compromised PyPI mirror or BGP hijack can substitute malicious build tools.  ``gem install fpm`` and ``choco install svn/zig`` are also not hash-verified.
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
   * - C-037
     - SLSA Source Provenance Attestation of repository governance controls
     - Low
     - Repudiation, Spoofing
     - DFT-31
     - Mitigates: Source Provenance Attestations are published via ``slsa-framework/slsa-source-corroborator`` on every push to ``main``.  These attestations prove the specific source-level governance controls applied on each commit: branch protection, mandatory code review, and ancestry enforcement (C-038).  Predicate type ``https://slsa.dev/source_provenance/v1`` is signed by GitHub Actions via Sigstore and stored in the GitHub Attestation registry.  Consumers can verify using ``gh attestation verify`` with ``--predicate-type https://slsa.dev/source_provenance/v1`` and ``--cert-identity`` pinned to ``source-provenance.yml@refs/heads/main``.  ``.github/workflows/source-provenance.yml``
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
     - Mitigates: Every dfetch release ships two complementary Sigstore-signed attestations that together let consumers trace the full source → binary chain.  SLSA build provenance (``source-provenance.yml``) on the source archive proves the archive was produced from the official tagged commit by the official CI workflow, recording the exact inputs used at build time.  A Verification Summary Attestation (VSA, ``build.yml``) on binary installers records that the source archive was itself attested and verified before the binary was produced, linking source-level trust to the installed package.  Both are signed by GitHub Actions via Sigstore and can be verified using ``gh attestation verify`` with ``--predicate-type https://slsa.dev/provenance/v1`` or ``--predicate-type https://slsa.dev/verification_summary/v1`` respectively.  This substantially mitigates DFT-31 (consumers now have attestations to verify against) and DFT-25 (forged provenance would fail Sigstore verification).  The formal SLSA Source Level attestation of governance controls is addressed by C-037.  ``doc/howto/verify-integrity.rst``
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
   * - C-025
     - No hardware-token MFA for release operations
     - High
     - Spoofing, Elevation of Privilege
     - DFT-11
     - Affects: No hardware-token (FIDO2/WebAuthn) MFA or mandatory second-approver sign-off is required for accounts with merge or release-trigger rights.  A compromised maintainer account - via phishing, credential stuffing, or SMS-TOTP bypass - can merge a backdoored PR and trigger the release workflow without any automated block.  Enforce FIDO2 MFA on all accounts with merge rights and add a required reviewer to the ``pypi`` deployment environment.

