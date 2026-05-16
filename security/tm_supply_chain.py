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

from security.tm_common import (  # noqa: E402  # pylint: disable=wrong-import-position
    THREATS_FILE,
    Control,
    ControlAssessment,
    apply_report_utils_patch,
    build_asset_controls_index,
    make_dev_env_boundary,
    make_supply_chain_assumptions,
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
        "``contents:write`` permission allows CI to upload SARIF results and release assets."
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
        "but execute with restricted permissions during CI (no access to production secrets).  "
        "A malicious PR modifying workflow files could attempt to exfiltrate secrets "
        "during the PR CI run, mitigated by ``ci.yml`` secret scoping (C-024) and "
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
    release_gate = Process("Release Gate / Code Review")
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
    gh_actions_workflow = Process("GitHub Actions Workflow")
    gh_actions_workflow.inBoundary = b_github
    gh_actions_workflow.description = (
        "CI/CD pipelines: test, build (wheel/msi/deb/rpm), lint, CodeQL, Scorecard, "
        "dependency-review, docs, release.  "
        "All actions pinned by commit SHA.  "
        "harden-runner used in every workflow that executes steps on a runner "
        "(egress: block with endpoint allowlist); ci.yml is a dispatcher-only workflow "
        "with no runner steps and does not include harden-runner."
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
    python_build = Process("Python Build (wheel / sdist)")
    python_build.inBoundary = b_github
    python_build.description = (
        "Runs ``python -m build`` to produce wheel and sdist.  "
        "Build deps (setuptools, build, fpm, gem) fetched from PyPI/RubyGems without "
        "hash pinning.  SLSA provenance attestations are generated by the release "
        "workflow."
    )
    python_build.controls.isHardened = (
        False  # build deps installed without --require-hashes; see gap C-023
    )
    python_build.controls.isCiPipeline = True  # CI/release pipeline build step
    return release_gate, gh_actions_workflow, python_build


def _make_sc_datastores(b_github: Boundary) -> tuple[Datastore, Datastore]:
    """Create data assets; return all for use in dataflows."""
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
        "CI runs triggered by pull requests.  ``persist-credentials:false`` on all "
        "checkout steps.  Runs with restricted permissions — no access to production "
        "secrets (see C-024)."
    )
    df13a.controls.isHardened = True

    df13b = Dataflow(gh_repository, gh_actions_runner, "DF-13b: Release CI checkout")
    df13b.description = (
        "GitHub Actions checks out the tagged commit from main (A-01) for release "
        "and build workflows.  ``persist-credentials:false`` on all checkout steps.  "
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
        "build (gap C-023)."
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
        "failure (gap C-023)."
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
        "CI runner uploads artifacts back to the repository: SARIF results to GitHub "
        "Code Scanning (CodeQL, Scorecard) and release assets.  "
        "Mitigated by: authenticated GitHub API (GITHUB_TOKEN scoped to ``security-events: write``), "
        "SHA-pinned upload actions."
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


def _make_sc_elements_and_flows(
    b_dev: Boundary,
    b_consumer: Boundary,
    b_github: Boundary,
    b_pypi: Boundary,
) -> None:
    """Create all supply-chain model elements and wire dataflows DF-11 through DF-26."""
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


def build_model() -> TM:
    """Construct and return the supply-chain threat model."""
    TM.reset()
    apply_report_utils_patch()
    model = TM(
        "dfetch Supply Chain",
        description=(
            "Threat model for dfetch.  "
            "Covers the pre-install lifecycle: code contribution, CI/CD, "
            "build (wheel / sdist), PyPI distribution, and consumer installation.  "
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


# ── CONTROLS AND GAPS ────────────────────────────────────────────────────────

CONTROLS: list[Control] = [
    # ── Implemented controls ─────────────────────────────────────────────────
    Control(
        id="C-009",
        name="Actions commit-SHA pinning",
        assets=["A-01", "A-02"],
        threats=["DFT-07"],
        reference=".github/workflows/*.yml",
        assessment=ControlAssessment(risk="High", stride=["Tampering"]),
        description=(
            "Every third-party GitHub Action is pinned to a full commit SHA, "
            "preventing tag-mutable supply-chain substitution."
        ),
    ),
    Control(
        id="C-010",
        name="OIDC trusted publishing",
        assets=["A-05", "A-03"],
        threats=["DFT-07"],
        reference=".github/workflows/python-publish.yml",
        assessment=ControlAssessment(
            risk="High", stride=["Spoofing", "Elevation of Privilege"]
        ),
        description=(
            "PyPI publishes via ``pypa/gh-action-pypi-publish`` with "
            "``id-token: write`` and no stored long-lived API token."
        ),
    ),
    Control(
        id="C-011",
        name="Minimal workflow permissions",
        assets=["A-01"],
        threats=["DFT-07"],
        reference=".github/workflows/*.yml",
        assessment=ControlAssessment(risk="Medium", stride=["Elevation of Privilege"]),
        description=(
            "Each workflow declares only the permissions it requires "
            "(default ``contents: read``)."
        ),
    ),
    Control(
        id="C-012",
        name="persist-credentials: false",
        assets=["A-01"],
        threats=["DFT-07"],
        reference=".github/workflows/*.yml",
        assessment=ControlAssessment(
            status="implemented", risk="Medium", stride=["Information Disclosure"]
        ),
        description=(
            "``persist-credentials: false`` is set on all checkout steps across "
            "all workflows that run on a runner.  The GitHub token is not persisted "
            "in the working tree after checkout."
        ),
    ),
    Control(
        id="C-013",
        name="Harden-runner (egress block)",
        assets=["A-01", "A-02"],
        threats=["DFT-07", "DFT-29"],
        reference=".github/workflows/*.yml",
        assessment=ControlAssessment(
            risk="High", stride=["Information Disclosure", "Tampering"]
        ),
        description=(
            "``step-security/harden-runner`` is used in every workflow with "
            "``egress-policy: block`` and an allowlist of permitted endpoints.  "
            "All non-allowlisted outbound connections are blocked."
        ),
    ),
    Control(
        id="C-015",
        name="CodeQL static analysis",
        assets=["A-01"],
        threats=["DFT-03", "DFT-06"],
        reference=".github/workflows/codeql-analysis.yml",
        assessment=ControlAssessment(
            risk="Medium", stride=["Tampering", "Elevation of Privilege"]
        ),
        description=(
            "CodeQL scans the Python codebase for security vulnerabilities on "
            "pushes and pull requests targeting ``main``, and on a weekly cron schedule."
        ),
    ),
    Control(
        id="C-016",
        name="Dependency review",
        assets=["A-07"],
        threats=["DFT-10"],
        reference=".github/workflows/dependency-review.yml",
        assessment=ControlAssessment(risk="Medium", stride=["Tampering"]),
        description=(
            "``actions/dependency-review-action`` checks for known vulnerabilities "
            "in newly added dependencies on every pull request."
        ),
    ),
    Control(
        id="C-017",
        name="bandit security linter",
        assets=["A-01"],
        threats=["DFT-03", "DFT-06"],
        reference="pyproject.toml",
        assessment=ControlAssessment(
            risk="Low", stride=["Tampering", "Elevation of Privilege"]
        ),
        description=(
            "``bandit -r dfetch`` runs in CI to detect common Python security issues."
        ),
    ),
    Control(
        id="C-021",
        name="Sigstore SBOM attestation",
        assets=["A-03"],
        threats=["DFT-05"],
        assessment=ControlAssessment(risk="Medium", stride=["Spoofing", "Tampering"]),
        description=(
            "The release pipeline generates CycloneDX SBOM attestations via "
            "``actions/attest`` with Sigstore signatures.  These attest the software "
            "composition (SBOM) of the published packages using predicate type "
            "``https://cyclonedx.org/bom``."
        ),
    ),
    Control(
        id="C-022",
        name="CycloneDX SBOM on PyPI",
        assets=["A-03", "A-07"],
        threats=["DFT-02"],
        assessment=ControlAssessment(risk="Low", stride=["Repudiation"]),
        description=(
            "A CycloneDX SBOM is generated during the build and published "
            "alongside the PyPI release, satisfying CRA Article 13 requirements."
        ),
    ),
    Control(
        id="C-024",
        name="``secrets: inherit`` scope",
        assets=["A-01", "A-05"],
        threats=["DFT-07"],
        assessment=ControlAssessment(risk="Medium", stride=["Information Disclosure"]),
        description=(
            "``ci.yml`` only passes required repository secrets to the test and "
            "docs workflows, preventing malicious PR steps from exfiltrating "
            "unrelated secrets."
        ),
    ),
    Control(
        id="C-026",
        name="Consumer-side package provenance verification",
        assets=["A-03"],
        threats=["DFT-17", "DFT-25"],
        assessment=ControlAssessment(
            status="implemented", risk="Medium", stride=["Spoofing", "Tampering"]
        ),
        reference="doc/tutorials/installation.rst#verifying-release-integrity",
        description=(
            "Consumers installing dfetch via ``pip install dfetch`` have access to "
            "documented procedures to verify the SBOM (CycloneDX) attestation of the "
            "PyPI wheel using the GitHub CLI (``gh attestation verify``).  "
            "Consumers installing binary packages (deb, rpm, pkg, msi) can verify "
            "SLSA build provenance, SBOM, and VSA attestations.  "
            "Consumers working from source can verify SLSA build provenance and in-toto "
            "test result attestations on the source archive.  "
            "Platform-specific instructions for Linux, macOS, and Windows are provided "
            "in ``doc/howto/verify-integrity.rst``.  "
            "This is an interim mitigation pending PEP 740 built-in support in pip.  "
            "Without this documentation, a compromised PyPI account, namespace-squatting, "
            "or dependency-confusion could serve malicious code undetected (DFT-17).  "
            "An attacker controlling the release pipeline could publish a plausible "
            "attestation alongside a backdoored wheel (DFT-25).  "
            "By providing clear, copy-paste instructions, we enable security-conscious "
            "consumers to verify provenance before installation."
        ),
    ),
    Control(
        id="C-032",
        name="Consumer attestation verification pins to release tag ref",
        assets=["A-01", "A-03"],
        threats=["DFT-27"],
        reference="doc/tutorials/installation.rst",
        assessment=ControlAssessment(
            status="implemented", risk="Medium", stride=["Tampering", "Spoofing"]
        ),
        description=(
            "All ``gh attestation verify`` commands in the installation guide use "
            "``--cert-identity`` pinned to the release workflow at a specific version "
            "tag (e.g. ``...python-publish.yml@refs/tags/v<version>`` for pip packages, "
            "``...build.yml@refs/tags/v<version>`` for binary installers) combined "
            "with ``--cert-oidc-issuer https://token.actions.githubusercontent.com``.  "
            "This rejects attestations produced by any workflow or branch other than "
            "the expected release workflow on an official version tag.  "
            "A build from an unofficial fork or unprotected branch would produce an "
            "attestation with a different cert-identity and fail verification."
        ),
    ),
    Control(
        id="C-033",
        name="Ref-scoped build cache keys isolate PR and release builds",
        assets=["A-08b"],
        threats=["DFT-28"],
        reference=".github/workflows/build.yml",
        assessment=ControlAssessment(
            status="implemented", risk="High", stride=["Tampering"]
        ),
        description=(
            "ccache and clcache keys in ``build.yml`` include ``${{ github.ref_name }}`` "
            "so cache entries written by a pull-request build are scoped to the PR's "
            "branch name and cannot be restored by a release-tag build.  "
            "A malicious fork PR step cannot pre-populate a cache slot that the release "
            "workflow will restore, because the release tag name is not reachable from "
            "the PR's branch ref."
        ),
    ),
    Control(
        id="C-037",
        name="SLSA Source Provenance Attestation of repository governance controls",
        assets=["A-01"],
        threats=["DFT-31"],
        reference=".github/workflows/source-provenance.yml",
        assessment=ControlAssessment(
            status="implemented", risk="Low", stride=["Repudiation", "Spoofing"]
        ),
        description=(
            "Source Provenance Attestations are published via "
            "``slsa-framework/slsa-source-corroborator`` on every push to ``main``.  "
            "These attestations prove the specific source-level governance controls "
            "applied on each commit: branch protection, mandatory code review, and "
            "ancestry enforcement (C-038).  "
            "Predicate type ``https://slsa.dev/source_provenance/v1`` is signed by "
            "GitHub Actions via Sigstore and stored in the GitHub Attestation registry.  "
            "Consumers can verify using ``gh attestation verify`` with "
            "``--predicate-type https://slsa.dev/source_provenance/v1`` and "
            "``--cert-identity`` pinned to ``source-provenance.yml@refs/heads/main``."
        ),
    ),
    Control(
        id="C-038",
        name="Ancestry enforcement on dfetch main branch",
        assets=["A-01"],
        threats=["DFT-33"],
        reference=".github/workflows/",
        assessment=ControlAssessment(
            status="implemented", risk="Low", stride=["Tampering"]
        ),
        description=(
            "GitHub branch-protection rules on the dfetch ``main`` branch prohibit "
            "force-pushes, satisfying the SLSA Source Level 2 ancestry-enforcement "
            "requirement.  The immutable revision lineage of the main branch is "
            "preserved: no contributor can rewrite history and orphan a "
            "previously-audited commit SHA.  Consumers who pin to a dfetch commit SHA "
            "can rely on that SHA remaining reachable indefinitely."
        ),
    ),
    Control(
        id="C-039",
        name="Source build provenance and VSA attestations",
        assets=["A-01", "A-02", "A-03"],
        threats=["DFT-31", "DFT-25"],
        reference="doc/howto/verify-integrity.rst",
        assessment=ControlAssessment(
            status="implemented",
            risk="High",
            stride=["Spoofing", "Tampering", "Repudiation"],
        ),
        description=(
            "Every dfetch release ships two complementary Sigstore-signed attestations "
            "that together let consumers trace the full source → binary chain.  "
            "SLSA build provenance (``source-provenance.yml``) on the source archive proves "
            "the archive was produced from the official tagged commit by the official CI "
            "workflow, recording the exact inputs used at build time.  "
            "A Verification Summary Attestation (VSA, ``build.yml``) on binary installers "
            "records that the source archive was itself attested and verified before the "
            "binary was produced, linking source-level trust to the installed package.  "
            "Both are signed by GitHub Actions via Sigstore and can be verified using "
            "``gh attestation verify`` with ``--predicate-type https://slsa.dev/provenance/v1`` "
            "or ``--predicate-type https://slsa.dev/verification_summary/v1`` respectively.  "
            "This substantially mitigates DFT-31 (consumers now have attestations to verify "
            "against) and DFT-25 (forged provenance would fail Sigstore verification).  "
            "The formal SLSA Source Level attestation of governance controls is addressed by C-037."
        ),
    ),
    Control(
        id="C-040",
        name="Test result attestation on source archive",
        assets=["A-01", "A-02"],
        threats=["DFT-31"],
        reference=".github/workflows/test.yml",
        assessment=ControlAssessment(
            status="implemented", risk="Medium", stride=["Repudiation", "Tampering"]
        ),
        description=(
            "The CI test workflow (``test.yml``) generates an in-toto test result "
            "attestation (predicate type ``https://in-toto.io/attestation/test-result/v0.1``) "
            "for every release and main-branch commit.  "
            "The attestation proves the full CI test suite ran against the exact source "
            "archive and every check passed, before any binary was produced from that source.  "
            "Consumers can verify it using "
            "``gh attestation verify dfetch-source.tar.gz`` with "
            "``--predicate-type https://in-toto.io/attestation/test-result/v0.1`` and "
            "``--cert-identity`` pinned to ``test.yml`` at the release tag ref.  "
            "This provides an additional layer of assurance beyond build provenance: "
            "not only was the artifact produced from the official commit, but the test "
            "suite demonstrably passed on that exact source before any binary was built."
        ),
    ),
    # ── Gaps ─────────────────────────────────────────────────────────────────
    Control(
        id="C-023",
        name="Build deps without hash pinning",
        assets=["A-07"],
        threats=["DFT-10"],
        assessment=ControlAssessment(status="gap", risk="High", stride=["Tampering"]),
        description=(
            "``pip install .`` and ``pip install --upgrade pip build`` in CI do not "
            "use ``--require-hashes``.  A compromised PyPI mirror can substitute "
            "malicious build tooling."
        ),
    ),
    Control(
        id="C-025",
        name="No hardware-token MFA for release operations",
        assets=["A-01", "A-03"],
        threats=["DFT-11"],
        assessment=ControlAssessment(
            status="gap", risk="High", stride=["Spoofing", "Elevation of Privilege"]
        ),
        description=(
            "No hardware-token (FIDO2/WebAuthn) MFA or mandatory second-approver "
            "sign-off is required for accounts with merge or release-trigger rights.  "
            "A compromised maintainer account - via phishing, credential stuffing, or "
            "SMS-TOTP bypass - can merge a backdoored PR and trigger the release "
            "workflow without any automated block.  "
            "Enforce FIDO2 MFA on all accounts with merge rights and add a required "
            "reviewer to the ``pypi`` deployment environment."
        ),
    ),
]

_SUPPLY_CHAIN_ASSET_IDS = {
    "A-01",
    "A-01b",
    "A-02",
    "A-03",
    "A-05",
    "A-07",
    "A-08b",
}
ASSET_CONTROLS: dict[str, list[Control]] = build_asset_controls_index(
    CONTROLS, _SUPPLY_CHAIN_ASSET_IDS
)

if __name__ == "__main__":
    run_model(build_model, CONTROLS)
