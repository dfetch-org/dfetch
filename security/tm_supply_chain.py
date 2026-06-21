# pylint: disable=too-many-lines
"""Supply-chain threat model for dfetch.

Scope: pre-install lifecycle - code contribution, CI/CD, build
(wheel / sdist), PyPI distribution, and consumer installation.
The installed dfetch package is the handoff point to ``tm_usage.py``.

Run::

    python -m security.tm_supply_chain --dfd
    python -m security.tm_supply_chain --seq
    python -m security.tm_supply_chain --report REPORT
"""

import os
import sys

# Ensure the security package is importable when loaded by Sphinx directive
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from pytm import (  # noqa: E402  # pylint: disable=wrong-import-position
    TM,
    Actor,
    Boundary,
    Classification,
    Data,
    Dataflow,
    Datastore,
    ExternalEntity,
    Process,
)

from security.tm_controls_data import (  # noqa: E402  # pylint: disable=wrong-import-position
    SC_CONTROLS as CONTROLS,
)
from security.tm_elements import (  # noqa: E402  # pylint: disable=wrong-import-position
    THREATS_FILE,
    Control,
    ThreatResponse,
    build_asset_controls_index,
    make_dev_env_boundary,
    make_supply_chain_assumptions,
)
from security.tm_render import (  # noqa: E402  # pylint: disable=wrong-import-position
    apply_report_utils_patch,
    run_model,
)


def _make_sc_boundaries() -> tuple[Boundary, Boundary, Boundary, Boundary]:
    """Create and return supply-chain trust boundaries."""
    b_dev = make_dev_env_boundary()
    b_consumer = Boundary("Consumer Environment")
    b_consumer.description = (
        "End-user workstation or downstream CI pipeline where dfetch is installed "
        "and invoked.  Distinct from the developer environment: no source checkout, "
        "no signing keys, no deploy access.  The consumer is trusted at invocation "
        "time but has no special relationship with the dfetch release infrastructure."
    )
    b_github = Boundary("GitHub Platform")
    b_github.description = (
        "GitHub-hosted infrastructure: repository, CI/CD runners, Actions workflows, "
        "build cache, and code-scanning results.  "
        "Egress traffic on runners is blocked (``harden-runner`` with "
        "``egress-policy: block``) with an allowlist of permitted endpoints; "
        "``ci.yml`` forwards only explicitly named secrets to child workflows "
        "(``CODACY_PROJECT_TOKEN`` to ``test.yml``, ``GH_DFETCH_ORG_DEPLOY`` "
        "to ``docs.yml``)."
    )
    b_pypi = Boundary("PyPI / TestPyPI")
    b_pypi.description = (
        "Python Package Index and its staging registry.  dfetch publishes via "
        "OIDC trusted publishing - no long-lived API token stored."
    )
    return b_dev, b_consumer, b_github, b_pypi


def _make_sc_actors_and_entities(
    b_dev: Boundary,
    b_consumer: Boundary,
    b_github: Boundary,
    b_pypi: Boundary,
) -> tuple[
    Actor, Actor, ExternalEntity, ExternalEntity, ExternalEntity, ExternalEntity
]:
    """Create actors and external entities; return all for use in dataflows."""
    developer = Actor("Developer / Contributor")
    developer.inBoundary = b_dev
    developer.description = (
        "Anyone who writes code for dfetch: core maintainers who push directly and "
        "cut releases, and external contributors who submit pull requests.  "
        "Maintainers are trusted at workstation time and are responsible for correct "
        "branch-protection and release workflow configuration.  "
        "External contributors are untrusted until their PR passes code review and CI."
    )
    consumer = Actor("Consumer / End User")
    consumer.inBoundary = b_consumer
    consumer.description = (
        "Installs dfetch from PyPI (``pip install dfetch``) or from binary installer, "
        "then invokes it on a developer workstation or in a CI pipeline.  "
        "Can verify five complementary attestation types using ``gh attestation verify`` as "
        "documented in the release-integrity guide (see C-026, C-037, C-039, C-040): "
        "SBOM attestation on the PyPI wheel; SBOM, SLSA build provenance, and VSA on binary "
        "installers; SLSA build provenance, in-toto test result attestation, and SLSA Source "
        "Provenance Attestation on the source archive and main-branch commits."
    )
    gh_repository = ExternalEntity("A-01: GitHub Repository (main / protected)")
    gh_repository.inBoundary = b_github
    gh_repository.classification = Classification.RESTRICTED
    gh_repository.description = (
        "The protected ``main`` branch: force-push disabled, merges require passing CI "
        "and at least one approving review.  Contains the authoritative workflow "
        "definitions (``.github/workflows/``), release tags, and published release assets.  "
        "Workflow files on main are what GitHub Actions actually executes — a PR cannot "
        "override them for its own CI run.  "
        "``contents:write`` permits CI to upload release assets to GitHub Releases.  "
        "SARIF code-scanning write-back (DF-19) is performed separately under ``security-events: write``."
    )
    gh_repository.controls.hasAccessControl = True
    gh_repository.controls.providesIntegrity = True
    gh_repository_branches = ExternalEntity(
        "A-01b: GitHub Repository (feature branches / PRs)"
    )
    gh_repository_branches.inBoundary = b_github
    gh_repository_branches.classification = Classification.RESTRICTED
    gh_repository_branches.description = (
        "Unprotected feature branches and fork PRs: no mandatory review, no CI-gate "
        "requirement to push.  Any authenticated GitHub user can open a PR modifying "
        "``.github/workflows/`` files; those changes are reviewed before merging to main "
        "but cannot execute during CI — GitHub enforces that PR CI runs use the workflow "
        "files from the protected main branch, not from the PR branch (see DF-12).  "
        "Any pre-merge CI that does execute runs with restricted permissions and no access "
        "to production secrets, further mitigated by ``ci.yml`` secret scoping (C-024) and "
        "harden-runner egress block (C-013)."
    )
    gh_actions_runner = ExternalEntity("A-02: GitHub Actions Infrastructure")
    gh_actions_runner.inBoundary = b_github
    gh_actions_runner.classification = Classification.RESTRICTED
    gh_actions_runner.description = (
        "Microsoft-operated ephemeral runner executing CI/CD workflows.  "
        "Egress policy is ``block`` with an explicit allowlist of permitted endpoints - "
        "non-allowlisted outbound connections are blocked at the kernel level by "
        "``step-security/harden-runner``."
    )
    pypi = ExternalEntity("A-03: PyPI / TestPyPI")
    pypi.inBoundary = b_pypi
    pypi.classification = Classification.SENSITIVE
    pypi.description = (
        "Python Package Index - both the registry service and the published dfetch "
        "wheel/sdist (https://pypi.org/project/dfetch/).  "
        "Published via OIDC trusted publishing; no long-lived API token stored.  "
        "A machine-readable CycloneDX SBOM is generated during the build and "
        "published alongside the release.  "
        "Account takeover, registry compromise, or namespace-squatting would affect "
        "every consumer installing dfetch."
    )
    pypi.controls.usesCodeSigning = (
        True  # Sigstore SBOM attestation (actions/attest; predicate cyclonedx.org/bom)
    )
    pypi.controls.isHardened = (
        True  # OIDC trusted publishing; no stored long-lived token
    )
    return (
        developer,
        consumer,
        gh_repository,
        gh_repository_branches,
        gh_actions_runner,
        pypi,
    )


def _make_sc_processes(b_github: Boundary) -> tuple[Process, Process, Process]:
    """Create CI/CD process elements; return all for use in dataflows."""
    release_gate = Process("A-04: Release Gate / Code Review")
    release_gate.inBoundary = b_github
    release_gate.description = (
        "Branch-protection rules and mandatory peer code review enforced before "
        "merging to the default branch.  Controls privileged operations: PR merge, "
        "direct push to main, and release-workflow trigger.  "
        "A compromised maintainer account with merge rights bypasses peer review "
        "and can trigger a malicious release without any automated block.  "
        "No hardware-token MFA or mandatory second-maintainer approval for release "
        "operations is currently enforced."
    )
    release_gate.controls.hasAccessControl = (
        True  # branch protection and required reviews exist
    )
    release_gate.controls.isHardened = (
        False  # account compromise bypasses the gate entirely
    )
    release_gate.controls.isCiPipeline = True  # CI/release pipeline gate
    gh_actions_workflow = Process("A-06: GitHub Actions Workflow")
    gh_actions_workflow.inBoundary = b_github
    gh_actions_workflow.description = (
        "CI/CD pipelines: test, build (wheel/msi/deb/rpm), lint, CodeQL, Scorecard, "
        "dependency-review, docs, release, winget-publish.  "
        "All actions pinned by commit SHA.  "
        "harden-runner used in every workflow that executes steps on a runner "
        "(egress: block with endpoint allowlist); ci.yml is a dispatcher-only workflow "
        "with no runner steps and does not include harden-runner.  "
        "winget-publish.yml uses a stored PAT (WINGET_TOKEN, A-10) to submit manifest "
        "PRs to the Winget Community Repository (A-09)."
    )
    gh_actions_workflow.controls.isHardened = (
        True  # SHA-pinned actions, harden-runner egress:block on all runner workflows
    )
    gh_actions_workflow.controls.providesIntegrity = (
        True  # CodeQL + Scorecard + dependency-review
    )
    gh_actions_workflow.controls.hasAccessControl = (
        True  # minimal permissions per workflow
    )
    gh_actions_workflow.controls.isCiPipeline = True  # CI/release pipeline
    python_build = Process("A-08: Python Build (wheel / sdist)")
    python_build.inBoundary = b_github
    python_build.description = (
        "Runs ``python -m build`` to produce wheel and sdist.  "
        "Build deps (setuptools, build, fpm, gem) fetched from PyPI/RubyGems without "
        "hash pinning.  SLSA provenance attestations are generated by the release "
        "workflow."
    )
    python_build.controls.isHardened = (
        False  # build deps installed without --require-hashes; no hash-pinning gap
    )
    python_build.controls.isCiPipeline = True  # CI/release pipeline build step
    return release_gate, gh_actions_workflow, python_build


def _make_sc_datastores(b_github: Boundary) -> tuple[Datastore, Datastore]:
    """Create data assets; return all for use in dataflows."""
    Data(
        "A-10: WINGET_TOKEN PAT",
        description=(
            "Long-lived classic GitHub Personal Access Token (fine-grained PATs are not "
            "supported by the ``vedantmgoyal9/winget-releaser`` action) with ``public_repo`` "
            "scope, stored as a GitHub Actions environment secret in the ``winget`` "
            "environment.  "
            "Used by ``winget-publish.yml`` to push a manifest branch to the pre-existing "
            "fork ``dfetch-org/winget-pkgs`` and open a PR against ``microsoft/winget-pkgs``.  "
            "Unlike the PyPI OIDC token (A-05) which is short-lived and not stored, "
            "this PAT persists indefinitely until rotated.  "
            "If exfiltrated from the CI environment, an attacker could submit "
            "fraudulent manifest PRs from outside the project's pipeline."
        ),
        classification=Classification.SECRET,
        isCredentials=True,
        isPII=False,
        isStored=True,
        isDestEncryptedAtRest=True,  # GitHub encrypts Actions secrets at rest
        isSourceEncryptedAtRest=True,
    )
    Data(
        "A-05: PyPI OIDC Identity",
        description=(
            "GitHub OIDC token exchanged for a short-lived PyPI publish credential.  "
            "No long-lived API token stored.  The token is scoped to the GitHub Actions "
            "environment named ``pypi``.  "
            "Risk: if the OIDC issuer or the PyPI trusted-publisher mapping is "
            "misconfigured, an attacker could mint a valid publish token."
        ),
        classification=Classification.SECRET,
        isCredentials=True,
        isPII=False,
        isStored=False,
        isDestEncryptedAtRest=False,
        isSourceEncryptedAtRest=True,
    )
    dfetch_dev_deps = Datastore("A-07: dfetch Build / Dev Dependencies")
    dfetch_dev_deps.inBoundary = b_github
    dfetch_dev_deps.description = (
        "Python packages installed during CI: setuptools, build, pylint, bandit, "
        "mypy, pytest, etc.  Ruby gem ``fpm`` for platform builds.  "
        "Installed via ``pip install .`` and ``pip install --upgrade pip build`` "
        "without ``--require-hashes`` - a compromised PyPI mirror or BGP hijack "
        "can substitute malicious build tools.  "
        "``gem install fpm`` and ``choco install svn/zig`` are also not hash-verified."
    )
    dfetch_dev_deps.storesSensitiveData = False
    dfetch_dev_deps.hasWriteAccess = False
    dfetch_dev_deps.isSQL = False
    dfetch_dev_deps.classification = Classification.RESTRICTED
    gh_actions_cache = Datastore("A-08b: GitHub Actions Build Cache")
    gh_actions_cache.inBoundary = b_github
    gh_actions_cache.description = (
        "GitHub Actions cache entries written and restored across pipeline runs.  "
        "Used to speed up dependency installation (pip, gem) and incremental builds.  "
        "Cache-poisoning from forked PRs (DFT-28, SLSA E6: poison the build cache) is "
        "mitigated by ref-scoped cache keys: build.yml includes "
        "``${{ github.ref_name }}`` in both ``key`` and ``restore-keys`` (C-033), "
        "which isolates PR and release caches per branch so a fork cannot write into "
        "the release cache namespace."
    )
    gh_actions_cache.storesSensitiveData = False
    gh_actions_cache.hasWriteAccess = (
        True  # both PR and release builds write to the cache
    )
    gh_actions_cache.isSQL = False
    gh_actions_cache.classification = Classification.RESTRICTED
    return dfetch_dev_deps, gh_actions_cache


def _make_sc_code_contribution_flows(
    developer: Actor,
    gh_repository_branches: ExternalEntity,
    release_gate: Process,
) -> None:
    """Create code-contribution and review dataflows (DF-11, DF-22); auto-register with TM."""
    df11 = Dataflow(developer, gh_repository_branches, "DF-11: Push commits / open PR")
    df11.description = (
        "Developer or contributor pushes commits or opens a pull request targeting a "
        "feature branch (A-01b).  The entry point for all code changes.  "
        "Workflow files in ``.github/workflows/`` can be modified by PRs but are "
        "reviewed before merging; ``ci.yml`` only passes required repository secrets "
        "to child workflows, preventing PR CI steps from exfiltrating unrelated secrets."
    )
    df11.protocol = "HTTPS"
    df11.controls.isEncrypted = True
    df11.controls.hasAccessControl = True
    df11.controls.providesIntegrity = True

    df22 = Dataflow(
        gh_repository_branches, release_gate, "DF-22: PR enters code review"
    )
    df22.description = (
        "Pull request from a feature branch (A-01b) flows into the Release Gate / "
        "Code Review process.  Branch-protection rules require passing CI status "
        "checks and at least one approving review before any merge to main is permitted."
    )
    df22.controls.hasAccessControl = True


def _make_sc_workflow_checkout_flows(
    gh_repository: ExternalEntity,
    gh_actions_workflow: Process,
    gh_repository_branches: ExternalEntity,
    gh_actions_runner: ExternalEntity,
) -> None:
    """Create workflow-definition and CI-checkout dataflows (DF-12, DF-13a/b); auto-register with TM."""
    df12 = Dataflow(
        gh_repository,
        gh_actions_workflow,
        "DF-12: Main branch workflows drive CI execution",
    )
    df12.description = (
        "The ``.github/workflows/*.yml`` YAML files on the protected main branch (A-01) "
        "define what GitHub Actions executes.  GitHub enforces that PR CI runs use the "
        "workflow files from the base branch (main), not from the PR branch — a malicious "
        "PR cannot override the workflow for its own CI run.  "
        "Mitigated by SHA-pinned actions, minimal permissions, and mandatory code review "
        "before any workflow change reaches main (C-009, C-011)."
    )
    df12.controls.isHardened = True

    df13a = Dataflow(
        gh_repository_branches, gh_actions_runner, "DF-13a: PR CI checkout"
    )
    df13a.description = (
        "GitHub Actions checks out source from the feature branch / PR (A-01b) for "
        "CI runs triggered by pull requests.  ``persist-credentials: false`` on all "
        "checkout steps in this workflow.  Runs with restricted permissions — no access "
        "to production secrets (see C-024)."
    )
    df13a.controls.isHardened = True

    df13b = Dataflow(gh_repository, gh_actions_runner, "DF-13b: Release CI checkout")
    df13b.description = (
        "GitHub Actions checks out the tagged commit from main (A-01) for release "
        "and build workflows.  ``persist-credentials: false`` on almost all checkout "
        "steps (see C-012 for justified exceptions).  "
        "All third-party actions pinned by commit SHA."
    )
    df13b.controls.isHardened = True
    df13b.controls.providesIntegrity = True


def _make_sc_cache_restore_flow(
    gh_actions_cache: Datastore,
    gh_actions_runner: ExternalEntity,
) -> None:
    """Create CI cache-restore dataflow (DF-14); auto-registers with TM."""
    df14 = Dataflow(gh_actions_cache, gh_actions_runner, "DF-14: CI cache restore")
    df14.description = (
        "GitHub Actions runner restores a previously written cache entry before "
        "running build steps.  Ref-scoped cache keys (C-033) ensure a release-tag build "
        "restores only entries written under the same ref, not those written by a less-privileged "
        "PR workflow.  Residual risk: if ref-scoped keys were removed or misconfigured, the release "
        "build could consume attacker-controlled artifacts."
    )
    df14.protocol = "HTTPS"
    df14.controls.isEncrypted = True


def _make_sc_build_step_flows(
    gh_actions_workflow: Process,
    python_build: Process,
    pypi: ExternalEntity,
    dfetch_dev_deps: Datastore,
    gh_actions_runner: ExternalEntity,
) -> None:
    """Create build-trigger, dep-fetch, build-tool-consume, and artifact-output flows (DF-15 to DF-17b)."""
    df15 = Dataflow(
        gh_actions_workflow, python_build, "DF-15: Workflow triggers build step"
    )
    df15.description = (
        "The executing workflow process invokes the Python Build step "
        "(``python -m build``) to produce wheel and sdist artefacts.  "
        "Build tools (setuptools, fpm, etc.) are installed without hash-pinning at this "
        "point; a compromised package from PyPI could execute arbitrary code during the "
        "build without triggering any hash verification."
    )

    df15b = Dataflow(
        python_build, gh_actions_runner, "DF-15b: Built wheel/sdist artifacts"
    )
    df15b.description = (
        "The Python Build step produces wheel and sdist artefacts, which are written to "
        "the runner filesystem and later consumed by the publish step (DF-24).  "
        "A compromised build tool (DF-17 gap) can tamper with the artefact content at "
        "this point before attestations are generated."
    )

    df16 = Dataflow(pypi, dfetch_dev_deps, "DF-16: CI fetches build/dev deps from PyPI")
    df16.description = (
        "The CI runner installs build and dev dependencies from public PyPI: "
        "setuptools, build, pylint, mypy, pytest, etc.  "
        "No ``--require-hashes`` flag is used, so a compromised PyPI mirror or BGP "
        "hijack can substitute malicious build tooling without triggering any checksum "
        "failure."
    )
    df16.protocol = "HTTPS"
    df16.controls.isEncrypted = True
    df16.controls.isNetworkFlow = True

    df17 = Dataflow(
        dfetch_dev_deps, python_build, "DF-17: Build tools consumed by build step"
    )
    df17.description = (
        "Installed build/dev dependencies (A-07) are consumed by the Python Build "
        "process.  If any dependency was substituted by an attacker (DF-16 gap), the "
        "malicious code runs here with runner-level privileges."
    )


def _make_sc_cache_write_flow(
    gh_actions_runner: ExternalEntity,
    gh_actions_cache: Datastore,
) -> None:
    """Create CI cache-write dataflow (DF-18); auto-registers with TM."""
    df18 = Dataflow(gh_actions_runner, gh_actions_cache, "DF-18: CI cache write")
    df18.description = (
        "GitHub Actions runner writes build cache entries (pip dependencies, gem packages, "
        "incremental build outputs) to the shared cache.  "
        "Cache keys in ``build.yml`` include ``${{ github.ref_name }}`` (C-033), isolating "
        "PR and release cache namespaces so a fork PR cannot write into the release cache slot.  "
        "Residual risk: if ref-scoped keys were removed or misconfigured, cache-poisoning "
        "from forks would be possible (DFT-28, SLSA E6)."
    )
    df18.protocol = "HTTPS"
    df18.controls.isEncrypted = True


def _make_sc_ci_reporting_flows(
    gh_actions_runner: ExternalEntity,
    gh_repository: ExternalEntity,
) -> None:
    """Create CI write-back dataflow (DF-19); auto-registers with TM."""
    df19 = Dataflow(
        gh_actions_runner,
        gh_repository,
        "DF-19: CI write-back (SARIF / artifacts)",
    )
    df19.description = (
        "CI runner uploads two categories of artifact back to the repository:  "
        "(1) SARIF results to GitHub Code Scanning (CodeQL, Scorecard) — "
        "GITHUB_TOKEN scoped to ``security-events: write``;  "
        "(2) release assets (wheel, binary installers, attestations) — "
        "GITHUB_TOKEN scoped to ``contents: write``.  "
        "Both paths use SHA-pinned upload actions and the authenticated GitHub API."
    )
    df19.protocol = "HTTPS"
    df19.controls.isEncrypted = True
    df19.controls.isHardened = True
    df19.controls.providesIntegrity = True
    df19.controls.hasAccessControl = True


def _make_sc_merge_flow(
    release_gate: Process,
    gh_repository: ExternalEntity,
) -> None:
    """Create approved-merge dataflow (DF-23); auto-registers with TM."""
    df23 = Dataflow(release_gate, gh_repository, "DF-23: Approved merge to main")
    df23.description = (
        "After peer review approval and all required CI checks pass, the Release Gate "
        "permits the merge.  The resulting commit on main may trigger downstream "
        "CI workflows including the release pipeline."
    )
    df23.controls.hasAccessControl = True
    df23.controls.providesIntegrity = True


def _make_sc_publish_flow(
    gh_actions_runner: ExternalEntity,
    pypi: ExternalEntity,
) -> None:
    """Create the PyPI publish dataflow (DF-24); auto-registers with TM."""
    df24 = Dataflow(gh_actions_runner, pypi, "DF-24: Publish wheel to PyPI (OIDC)")
    df24.description = (
        "On release event, the GitHub Actions runner uses ``pypa/gh-action-pypi-publish`` "
        "with OIDC trusted publishing to upload the wheel and sdist produced by the Python "
        "Build step to PyPI (A-03).  No long-lived API token "
        "is stored; the OIDC token is scoped to the ``pypi`` deployment environment.  "
        "Four attestation types are generated and anchored in Sigstore: "
        "SLSA build provenance, SBOM (CycloneDX), VSA on binary installers, and in-toto "
        "test result attestation on the source archive (C-021, C-039, C-040)."
    )
    df24.protocol = "HTTPS"
    df24.controls.isEncrypted = True
    df24.controls.isHardened = (
        True  # OIDC token exchange; no long-lived credential in transit
    )
    df24.controls.providesIntegrity = True
    df24.controls.usesCodeSigning = True  # Sigstore attestations via actions/attest


def _make_sc_consumer_install_flows(
    consumer: Actor,
    pypi: ExternalEntity,
) -> None:
    """Create consumer pip-install and download dataflows (DF-25, DF-26); auto-register with TM."""
    df25 = Dataflow(consumer, pypi, "DF-25: pip install dfetch")
    df25.description = (
        "Consumer installs dfetch from PyPI.  The installed wheel contains the dfetch "
        "CLI; the handoff to the runtime-usage model occurs when the consumer invokes "
        "dfetch with a manifest.  "
        "The consumer can verify the SBOM (CycloneDX) attestation of the wheel using "
        "``gh attestation verify`` with ``--predicate-type https://cyclonedx.org/bom`` "
        "and cert-identity pinned to ``python-publish.yml`` (see C-026)."
    )
    df25.protocol = "HTTPS"
    df25.controls.isEncrypted = True
    df25.controls.isNetworkFlow = True

    df26 = Dataflow(pypi, consumer, "DF-26: Consumer downloads dfetch from PyPI")
    df26.description = (
        "The published dfetch wheel (A-03) is downloaded to the consumer workstation "
        "during ``pip install dfetch``.  The consumer can verify the SBOM (CycloneDX) "
        "attestation using ``gh attestation verify`` as documented in C-026.  "
        "Without verification, a compromised PyPI account or namespace-squatting "
        "could serve a malicious package undetected (DFT-17)."
    )
    df26.protocol = "HTTPS"
    df26.controls.isEncrypted = True
    df26.controls.isNetworkFlow = True


def _make_sc_winget_elements_and_flows(
    gh_actions_runner: ExternalEntity,
    consumer: Actor,
) -> None:
    """Create Winget community-repo assets and publishing/installation flows (DF-27 through DF-29)."""
    b_winget = Boundary("Winget Community Repository")
    b_winget.description = (
        "The Windows Package Manager Community Repository "
        "(https://github.com/microsoft/winget-pkgs) where dfetch's Winget manifest "
        "is hosted.  "
        "Manifest PRs are submitted automatically by the CI release pipeline "
        "(winget-publish.yml) using the stored WINGET_TOKEN PAT (A-10).  "
        "Consumer installations resolve manifests from this repository; winget "
        "downloads the MSI installer from the URL declared in the manifest "
        "(pointing to GitHub Releases, A-01) and verifies its SHA256 hash."
    )

    winget_repo = ExternalEntity(
        "A-09: Winget Community Repository (microsoft/winget-pkgs)"
    )
    winget_repo.inBoundary = b_winget
    winget_repo.classification = Classification.SENSITIVE
    winget_repo.description = (
        "The Windows Package Manager Community Repository where the dfetch "
        "``DFetch-org.DFetch`` manifest is hosted "
        "(https://github.com/microsoft/winget-pkgs).  "
        "CI submits manifest update PRs via ``vedantmgoyal9/winget-releaser`` using "
        "a stored PAT (A-10); PRs are reviewed by ``microsoft/winget-pkgs`` "
        "maintainers before merging (C-041).  "
        "Manifests contain SHA256 hashes of the installer binary; winget verifies "
        "the hash before installation.  "
        "A compromised PAT or a fraudulent PR that passes review could redirect "
        "consumers to a malicious installer (DFT-35)."
    )
    winget_repo.controls.hasAccessControl = True  # PAT required to submit PRs
    winget_repo.controls.providesIntegrity = (
        True  # manifests contain SHA256 installer hashes
    )
    winget_repo.controls.usesCodeSigning = (
        False  # manifests are not cryptographically signed by the project
    )
    winget_repo.controls.isHardened = (
        False  # relies on manual community PR review, not automated technical controls
    )

    df27 = Dataflow(
        gh_actions_runner,
        winget_repo,
        "DF-27: Winget manifest PR submission",
    )
    df27.description = (
        "On release event, ``winget-publish.yml`` uses ``vedantmgoyal9/winget-releaser`` "
        "to discover the MSI asset in the GitHub release, compute its SHA256 hash, "
        "generate updated Winget manifests, and submit a PR to A-09 "
        "(``microsoft/winget-pkgs``) authenticated via the WINGET_TOKEN PAT (A-10).  "
        "The PR is reviewed by ``microsoft/winget-pkgs`` maintainers before merging "
        "(C-041).  "
        "Residual risk: a compromised PAT (DFT-34) or a fraudulent submission that "
        "passes review could redirect consumers to a malicious installer (DFT-35)."
    )
    df27.protocol = "HTTPS"
    df27.controls.isEncrypted = True
    df27.controls.isHardened = True  # harden-runner egress block; SHA-pinned action
    df27.controls.hasAccessControl = True  # WINGET_TOKEN PAT authentication
    df27.controls.isNetworkFlow = True
    df27.controls.providesIntegrity = (
        True  # action computes SHA256 of MSI and embeds it in manifest
    )

    df28 = Dataflow(consumer, winget_repo, "DF-28: winget install dfetch")
    df28.description = (
        "Consumer runs ``winget install -e --id DFetch-org.DFetch``.  "
        "The winget client resolves the manifest from A-09 (``microsoft/winget-pkgs``).  "
        "The manifest contains the installer URL (pointing to GitHub Releases, A-01) "
        "and the SHA256 hash of the MSI.  "
        "The consumer can verify the MSI attestations using ``gh attestation verify`` "
        "as documented in C-026 and C-039."
    )
    df28.protocol = "HTTPS"
    df28.controls.isEncrypted = True
    df28.controls.isNetworkFlow = True
    df28.controls.providesIntegrity = True  # winget verifies SHA256 hash from manifest

    df29 = Dataflow(winget_repo, consumer, "DF-29: Consumer downloads MSI via winget")
    df29.description = (
        "winget resolves the installer URL from the manifest in A-09 and downloads "
        "the MSI directly from GitHub Releases (A-01).  "
        "The SHA256 hash declared in the manifest is verified against the downloaded "
        "binary before installation begins.  "
        "The consumer can additionally verify SLSA build provenance, SBOM, and VSA "
        "attestations using ``gh attestation verify`` as documented in C-026 and C-039."
    )
    df29.protocol = "HTTPS"
    df29.controls.isEncrypted = True
    df29.controls.providesIntegrity = True  # SHA256 hash in manifest verified by winget
    df29.controls.isNetworkFlow = True


def _make_sc_elements_and_flows(
    b_dev: Boundary,
    b_consumer: Boundary,
    b_github: Boundary,
    b_pypi: Boundary,
) -> None:
    """Create all supply-chain model elements and wire dataflows DF-11 through DF-29."""
    (
        developer,
        consumer,
        gh_repository,
        gh_repository_branches,
        gh_actions_runner,
        pypi,
    ) = _make_sc_actors_and_entities(b_dev, b_consumer, b_github, b_pypi)
    release_gate, gh_actions_workflow, python_build = _make_sc_processes(b_github)
    dfetch_dev_deps, gh_actions_cache = _make_sc_datastores(b_github)
    # Lifecycle: commit/PR → CI → review → merge → publish → consumer install
    _make_sc_code_contribution_flows(developer, gh_repository_branches, release_gate)
    _make_sc_workflow_checkout_flows(
        gh_repository, gh_actions_workflow, gh_repository_branches, gh_actions_runner
    )
    _make_sc_cache_restore_flow(gh_actions_cache, gh_actions_runner)
    _make_sc_build_step_flows(
        gh_actions_workflow, python_build, pypi, dfetch_dev_deps, gh_actions_runner
    )
    _make_sc_cache_write_flow(gh_actions_runner, gh_actions_cache)
    _make_sc_ci_reporting_flows(gh_actions_runner, gh_repository)
    _make_sc_merge_flow(release_gate, gh_repository)
    _make_sc_publish_flow(gh_actions_runner, pypi)
    _make_sc_consumer_install_flows(consumer, pypi)
    _make_sc_winget_elements_and_flows(gh_actions_runner, consumer)


def build_model() -> TM:
    """Construct and return the supply-chain threat model."""
    TM.reset()
    apply_report_utils_patch()
    model = TM(
        "dfetch Supply Chain",
        description=(
            "Threat model for dfetch.  "
            "Covers the pre-install lifecycle: code contribution, CI/CD, "
            "build (wheel / sdist), PyPI distribution, Winget manifest submission, "
            "and consumer installation.  "
            "The installed dfetch package is the handoff point to tm_usage.py."
        ),
        isOrdered=True,
        mergeResponses=True,
        threatsFile=THREATS_FILE,
    )
    model.assumptions = make_supply_chain_assumptions()
    b_dev, b_consumer, b_github, b_pypi = _make_sc_boundaries()
    _make_sc_elements_and_flows(b_dev, b_consumer, b_github, b_pypi)
    return model


_SUPPLY_CHAIN_ASSET_IDS = {
    "A-01",
    "A-01b",
    "A-02",
    "A-03",
    "A-04",
    "A-05",
    "A-06",
    "A-07",
    "A-08",
    "A-08b",
    "A-09",
    "A-10",
}
ASSET_CONTROLS: dict[str, list[Control]] = build_asset_controls_index(
    CONTROLS, _SUPPLY_CHAIN_ASSET_IDS
)

RESPONSES: list[ThreatResponse] = [
    ThreatResponse(
        "DFT-02",
        "mitigate",
        risk="High",
        stride=["Tampering", "Spoofing"],
        target="A-03: PyPI / TestPyPI",
    ),
    ThreatResponse(
        "DFT-03",
        "mitigate",
        risk="Medium",
        stride=["Tampering", "Elevation of Privilege"],
        target="A-08: Python Build (wheel / sdist)",
    ),
    ThreatResponse(
        "DFT-05",
        "mitigate",
        risk="Medium",
        stride=["Tampering", "Spoofing"],
        target="DF-16: CI fetches build/dev deps from PyPI",
    ),
    ThreatResponse(
        "DFT-06",
        "mitigate",
        risk="High",
        stride=["Tampering", "Elevation of Privilege"],
        note=(
            "C-015 (CodeQL) and C-017 (bandit) perform static analysis that detects "
            "command injection patterns before code reaches production."
        ),
    ),
    ThreatResponse(
        "DFT-07",
        "mitigate",
        risk="High",
        stride=[
            "Spoofing",
            "Tampering",
            "Information Disclosure",
            "Elevation of Privilege",
        ],
        target="A-08: Python Build (wheel / sdist)",
    ),
    ThreatResponse(
        "DFT-08",
        "accept",
        risk="High",
        stride=["Tampering"],
        note=(
            "Secondary artifacts are not independently verified in the supply-chain pipeline.  "
            "Accepted based on the **CI runner posture** assumption: GitHub Actions environments "
            "run on ephemeral, GitHub-hosted runners whose isolation is provided by GitHub, so "
            "secondary artifacts written and consumed within a single job are considered "
            "adequately protected by that isolation."
        ),
    ),
    ThreatResponse(
        "DFT-09",
        "accept",
        risk="Medium",
        stride=["Denial of Service"],
        note=(
            "Decompression-bomb protection is a runtime concern (C-002 in usage model), "
            "not a supply-chain pipeline control.  "
            "Accepted based on the **CI runner posture** assumption: GitHub Actions environments "
            "run on ephemeral, isolated runners; any denial-of-service impact from a "
            "decompression bomb is bounded to the affected job and does not persist beyond it."
        ),
        target="A-08: Python Build (wheel / sdist)",
    ),
    ThreatResponse(
        "DFT-10",
        "mitigate",
        risk="High",
        stride=["Tampering"],
        note="C-016 checks known-vulnerable deps on PRs; build deps lack ``--require-hashes`` pinning.",
    ),
    ThreatResponse(
        "DFT-11",
        "accept",
        risk="High",
        stride=["Spoofing", "Elevation of Privilege"],
        note=(
            "No hardware-token MFA or mandatory second-approver enforced "
            "for accounts with merge or release-trigger rights.  "
            "Accepted based on the **Trusted workstation** assumption: developer "
            "workstations and accounts are trusted at development and commit time; "
            "a compromised maintainer account is outside the scope of this model."
        ),
    ),
    ThreatResponse(
        "DFT-17",
        "mitigate",
        risk="Medium",
        stride=["Spoofing"],
        target="A-03: PyPI / TestPyPI",
    ),
    ThreatResponse(
        "DFT-18",
        "accept",
        risk="High",
        stride=["Tampering", "Spoofing"],
        note=(
            "Namespace-squatting on PyPI is a registry-level concern outside dfetch's control.  "
            "Accepted based on the **CI runner posture** assumption: GitHub Actions environments "
            "inherit the security posture of the GitHub-hosted runner, including its access to "
            "the public PyPI registry; registry-level namespace integrity is outside the scope "
            "of this model."
        ),
    ),
    ThreatResponse(
        "DFT-20",
        "accept",
        risk="Medium",
        stride=["Spoofing", "Tampering"],
        note=(
            "Abandoned namespace reclaim is a registry-level concern outside dfetch's control.  "
            "Accepted based on the **CI runner posture** assumption: GitHub Actions environments "
            "inherit the security posture of the GitHub-hosted runner, including its access to "
            "the public PyPI registry; registry-level namespace integrity is outside the scope "
            "of this model."
        ),
    ),
    ThreatResponse(
        "DFT-23",
        "accept",
        risk="Medium",
        stride=["Tampering"],
        note=(
            "No version-pinning or update-freshness check in the supply-chain pipeline.  "
            "Accepted based on the **CI runner posture** assumption: GitHub Actions environments "
            "inherit the security posture of the GitHub-hosted runner; freshness enforcement "
            "for registry dependencies is a registry-level concern outside the scope of this "
            "model."
        ),
        target="DF-16: CI fetches build/dev deps from PyPI",
    ),
    ThreatResponse(
        "DFT-24",
        "accept",
        risk="High",
        stride=["Tampering"],
        note=(
            "Build-artifact cache is ref-scoped (C-033); "
            "pipeline metadata store is not independently integrity-protected.  "
            "Accepted based on the **CI runner posture** assumption: GitHub Actions environments "
            "run on ephemeral, GitHub-hosted runners; the ref-scoped cache key isolation "
            "provided by that environment is considered sufficient for the pipeline metadata."
        ),
    ),
    ThreatResponse(
        "DFT-25",
        "mitigate",
        risk="High",
        stride=["Spoofing", "Tampering", "Repudiation"],
    ),
    ThreatResponse(
        "DFT-27",
        "mitigate",
        risk="High",
        stride=["Tampering", "Spoofing"],
        target="A-04: Release Gate / Code Review",
    ),
    ThreatResponse("DFT-28", "mitigate", risk="High", stride=["Tampering"]),
    ThreatResponse(
        "DFT-29",
        "mitigate",
        risk="High",
        stride=["Information Disclosure", "Tampering"],
        target="A-08: Python Build (wheel / sdist)",
    ),
    ThreatResponse(
        "DFT-31",
        "mitigate",
        risk="Low",
        stride=["Repudiation", "Spoofing"],
        target="DF-26: Consumer downloads dfetch from PyPI",
    ),
    ThreatResponse(
        "DFT-33",
        "mitigate",
        risk="Low",
        stride=["Tampering"],
        target="DF-26: Consumer downloads dfetch from PyPI",
    ),
    ThreatResponse(
        "DFT-34",
        "mitigate",
        risk="High",
        stride=["Information Disclosure", "Tampering"],
        target="A-10: WINGET_TOKEN PAT",
    ),
    ThreatResponse(
        "DFT-35",
        "mitigate",
        risk="High",
        stride=["Tampering", "Spoofing"],
        target="A-09: Winget Community Repository (microsoft/winget-pkgs)",
    ),
]

if __name__ == "__main__":
    run_model(build_model, CONTROLS, RESPONSES)
