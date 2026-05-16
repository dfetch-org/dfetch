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
    make_attacker_profiles,
    make_dev_env_boundary,
    make_network_boundary,
    make_supply_chain_assumptions,
    run_model,
)


def _make_sc_boundaries() -> tuple[Boundary, Boundary, Boundary, Boundary]:
    """Create and return supply-chain trust boundaries."""
    b_dev = make_dev_env_boundary()
    b_github = Boundary("GitHub Actions Infrastructure")
    b_github.description = (
        "Microsoft-operated ephemeral runners executing the CI/CD workflows.  "
        "Egress traffic is blocked (``harden-runner`` with ``egress-policy: block``) "
        "with an allowlist of permitted endpoints; ``ci.yml`` forwards only "
        "explicitly named secrets to child workflows (``CODACY_PROJECT_TOKEN`` "
        "to ``test.yml``, ``GH_DFETCH_ORG_DEPLOY`` to ``docs.yml``)."
    )
    b_pypi = Boundary("PyPI / TestPyPI")
    b_pypi.description = (
        "Python Package Index and its staging registry.  dfetch publishes via "
        "OIDC trusted publishing - no long-lived API token stored."
    )
    b_net = make_network_boundary(
        description=(
            "Public internet - upstream package registries, PyPI, GitHub, CDN nodes, "
            "and other external endpoints reachable by the CI/CD infrastructure."
        )
    )
    return b_dev, b_github, b_pypi, b_net


def _make_sc_actors_and_entities(
    b_dev: Boundary,
    b_github: Boundary,
    b_pypi: Boundary,
    b_net: Boundary,
) -> tuple[Actor, Actor, ExternalEntity, ExternalEntity, ExternalEntity]:
    """Create actors and external entities; return those referenced by dataflows."""
    developer = Actor("Developer")
    developer.inBoundary = b_dev
    developer.description = (
        "dfetch project contributor: writes code, reviews PRs, cuts releases.  "
        "Trusted at workstation time; responsible for correct branch-protection "
        "and release workflow configuration."
    )
    contributor = Actor("Contributor / Attacker")
    contributor.inBoundary = b_net
    contributor.description = (
        "External contributor submitting pull requests, or an adversary attempting "
        "supply-chain manipulation (malicious PR, action-poisoning, or MITM on CI "
        "network traffic).  Code review, branch protection, and SHA-pinned Actions "
        "are the primary controls at this boundary."
    )
    consumer = Actor("Consumer / End User")
    consumer.inBoundary = b_dev
    consumer.description = (
        "Installs dfetch from PyPI (``pip install dfetch``) or from binary installer, "
        "then invokes it on a developer workstation or in a CI pipeline.  "
        "Can verify five complementary attestation types using ``gh attestation verify`` as "
        "documented in the release-integrity guide (see C-026, C-037, C-039, C-040): "
        "SBOM attestation on the PyPI wheel; SBOM, SLSA build provenance, and VSA on binary "
        "installers; SLSA build provenance, in-toto test result attestation, and SLSA Source "
        "Provenance Attestation on the source archive and main-branch commits."
    )
    gh_repository = ExternalEntity("A-01: GitHub Repository")
    gh_repository.inBoundary = b_github
    gh_repository.classification = Classification.RESTRICTED
    gh_repository.description = (
        "Source code, PRs, releases, and workflow definitions.  "
        "GitHub Actions workflows (``.github/workflows/``) with "
        "``contents:write`` permission can modify repository state and trigger releases."
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
    pypi.classification = Classification.PUBLIC
    pypi.description = (
        "Python Package Index.  dfetch is published via OIDC trusted publishing "
        "(no long-lived API token).  Account takeover or registry compromise "
        "would affect every consumer installing dfetch."
    )
    return contributor, consumer, gh_repository, gh_actions_runner, pypi


def _make_sc_processes(b_github: Boundary) -> None:
    """Create CI/CD process elements; all auto-register with TM."""
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


def _make_sc_datastores(b_github: Boundary, b_pypi: Boundary) -> Datastore:
    """Create data assets; return gh_actions_cache (referenced by dataflows)."""
    pypi_package = Datastore("A-04: dfetch PyPI Package")
    pypi_package.inBoundary = b_pypi
    pypi_package.description = (
        "Published wheel and sdist on PyPI (https://pypi.org/project/dfetch/).  "
        "Published via OIDC trusted publishing - no long-lived API token stored.  "
        "A machine-readable CycloneDX SBOM is generated during the build and "
        "published alongside the release.  "
        "Compromise of the PyPI account or registry affects every consumer."
    )
    pypi_package.storesSensitiveData = False
    pypi_package.hasWriteAccess = True  # publish pipeline writes new releases
    pypi_package.isSQL = False
    pypi_package.classification = Classification.SENSITIVE
    pypi_package.controls.usesCodeSigning = (
        True  # Sigstore SBOM attestation (actions/attest; predicate cyclonedx.org/bom)
    )
    pypi_package.controls.isHardened = (
        True  # OIDC trusted publishing; no stored long-lived token
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
    scorecard_results = Datastore("A-06: OpenSSF Scorecard Results")
    scorecard_results.inBoundary = b_github
    scorecard_results.description = (
        "Weekly OSSF Scorecard SARIF results uploaded to GitHub Code Scanning.  "
        "Covers: branch-protection, CI-tests, code-review, maintained, packaging, "
        "pinned-dependencies, SAST, signed-releases, token-permissions, vulnerabilities, "
        "dangerous-workflow, binary-artifacts, fuzzing, license, CII-best-practices, "
        "security-policy, webhooks.  "
        "Suppression or forgery hides supply-chain regressions."
    )
    scorecard_results.storesSensitiveData = False
    scorecard_results.hasWriteAccess = (
        True  # CI runner writes SARIF uploads here (DF-17)
    )
    scorecard_results.isSQL = False
    scorecard_results.classification = Classification.RESTRICTED
    scorecard_results.controls.providesIntegrity = (
        True  # authenticated output from OSSF Scorecard action
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
    gh_workflows = Datastore("A-08: GitHub Actions Workflows")
    gh_workflows.inBoundary = b_github
    gh_workflows.description = (
        "``.github/workflows/*.yml`` - CI/CD configuration checked into the repository.  "
        "11 workflows: ci, build, run, test, docs, release, python-publish, "
        "dependency-review, codeql-analysis, scorecard, devcontainer.  "
        "A malicious PR that modifies workflows can exfiltrate secrets or publish "
        "a backdoored release.  "
        "Mitigated by: SHA-pinned actions, persist-credentials:false, minimal permissions."
    )
    gh_workflows.storesSensitiveData = False
    gh_workflows.hasWriteAccess = True  # PRs can modify .github/workflows/ definitions
    gh_workflows.isSQL = False
    gh_workflows.classification = Classification.RESTRICTED
    gh_workflows.controls.isHardened = True
    gh_workflows.controls.providesIntegrity = (
        True  # branch protection + mandatory code review
    )
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
    return gh_actions_cache


def _make_sc_contrib_flows(
    contributor: Actor,
    consumer: Actor,
    gh_repository: ExternalEntity,
    pypi: ExternalEntity,
) -> None:
    """Create contributor- and consumer-facing dataflows; all auto-register with TM."""
    df11 = Dataflow(contributor, gh_repository, "DF-11: Submit pull request")
    df11.description = (
        "External contributor opens a PR against the dfetch repository.  "
        "Workflow files in ``.github/workflows/`` can be modified by PRs.  "
        "``ci.yml`` only passes required repository secrets to the test and docs "
        "workflows, preventing malicious PR steps from exfiltrating secrets."
    )
    df11.protocol = "HTTPS"
    df11.controls.hasAccessControl = True
    df11.controls.isHardened = (
        True  # git commit SHAs provide content-addressable integrity
    )
    df11.controls.providesIntegrity = True
    df14 = Dataflow(consumer, pypi, "DF-14: pip install dfetch")
    df14.description = (
        "Consumer installs dfetch from PyPI.  The installed wheel contains the dfetch "
        "CLI; the handoff to the runtime-usage model occurs when the consumer invokes "
        "dfetch with a manifest.  "
        "The consumer can verify the SBOM (CycloneDX) attestation of the wheel using "
        "``gh attestation verify`` with ``--predicate-type https://cyclonedx.org/bom`` "
        "and cert-identity pinned to ``python-publish.yml`` (see C-026)."
    )
    df14.protocol = "HTTPS"
    df14.controls.isEncrypted = True
    df14.controls.isNetworkFlow = True


def _make_sc_ci_flows(
    gh_repository: ExternalEntity,
    gh_actions_runner: ExternalEntity,
    pypi: ExternalEntity,
    gh_actions_cache: Datastore,
) -> None:
    """Create CI infrastructure dataflows; all auto-register with TM."""
    df12 = Dataflow(gh_repository, gh_actions_runner, "DF-12: CI checkout and build")
    df12.description = (
        "GitHub Actions checks out source, installs deps, runs tests, lints, builds.  "
        "``persist-credentials:false`` on all checkout steps.  "
        "All third-party actions pinned by commit SHA."
    )
    df12.controls.isHardened = True
    df12.controls.providesIntegrity = True
    df13 = Dataflow(gh_actions_runner, pypi, "DF-13: Publish to PyPI (OIDC)")
    df13.description = (
        "On release event, wheel/sdist uploaded to PyPI via "
        "``pypa/gh-action-pypi-publish``.  OIDC trusted publishing: no stored API token.  "
        "Four attestation types are generated by the release pipeline and anchored in Sigstore: "
        "SLSA build provenance, SBOM (CycloneDX), VSA (Verification Summary Attestation) on "
        "binary installers, and in-toto test result attestation on the source archive."
    )
    df13.protocol = "HTTPS"
    df13.controls.isEncrypted = True
    df13.controls.isHardened = (
        True  # OIDC token exchange; no long-lived credential in transit
    )
    df13.controls.providesIntegrity = (
        True  # Sigstore SBOM attestation covers published artifacts
    )
    df13.controls.usesCodeSigning = True  # SBOM attestation via actions/attest
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
    df19 = Dataflow(gh_actions_cache, gh_actions_runner, "DF-19: CI cache restore")
    df19.description = (
        "GitHub Actions runner restores a previously written cache entry before "
        "running build steps.  Ref-scoped cache keys (C-033) ensure a release-tag build "
        "restores only entries written under the same ref, not those written by a less-privileged "
        "PR workflow.  Residual risk: if ref-scoped keys were removed or misconfigured, the release "
        "build could consume attacker-controlled artifacts."
    )
    df19.protocol = "HTTPS"
    df19.controls.isEncrypted = True
    df17 = Dataflow(
        gh_actions_runner,
        gh_repository,
        "DF-17: CI write-back (SARIF / artifacts / cache)",
    )
    df17.description = (
        "CI runner uploads artifacts back to the repository: SARIF results to GitHub "
        "Code Scanning (CodeQL, Scorecard), release assets, and build cache.  "
        "Suppression or falsification of SARIF uploads (A-06) would hide supply-chain "
        "regressions from the security dashboard.  "
        "Mitigated by: authenticated GitHub API (GITHUB_TOKEN scoped to ``security-events: write``), "
        "SHA-pinned upload actions."
    )
    df17.protocol = "HTTPS"
    df17.controls.isEncrypted = True
    df17.controls.isHardened = (
        True  # GITHUB_TOKEN is scoped; harden-runner blocks exfiltration
    )
    df17.controls.providesIntegrity = True
    df17.controls.hasAccessControl = (
        True  # GITHUB_TOKEN permission scoping per workflow
    )


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
    model.assumptions = make_supply_chain_assumptions() + make_attacker_profiles()
    b_dev, b_github, b_pypi, b_net = _make_sc_boundaries()
    contributor, consumer, gh_repository, gh_actions_runner, pypi = (
        _make_sc_actors_and_entities(b_dev, b_github, b_pypi, b_net)
    )
    _make_sc_processes(b_github)
    gh_actions_cache = _make_sc_datastores(b_github, b_pypi)
    _make_sc_contrib_flows(contributor, consumer, gh_repository, pypi)
    _make_sc_ci_flows(gh_repository, gh_actions_runner, pypi, gh_actions_cache)
    return model


# ── CONTROLS AND GAPS ────────────────────────────────────────────────────────

CONTROLS: list[Control] = [
    # ── Implemented controls ─────────────────────────────────────────────────
    Control(
        id="C-009",
        name="Actions commit-SHA pinning",
        assets=["A-08", "A-02"],
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
        assets=["A-05", "A-04"],
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
        assets=["A-08"],
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
        assets=["A-08", "A-01"],
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
        assets=["A-08", "A-02"],
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
        id="C-014",
        name="OpenSSF Scorecard",
        assets=["A-01", "A-06"],
        threats=["DFT-07", "DFT-10"],
        reference=".github/workflows/scorecard.yml",
        assessment=ControlAssessment(risk="Low", stride=["Tampering"]),
        description=(
            "Weekly OSSF Scorecard analysis uploaded to GitHub Code Scanning "
            "covers the full set of OpenSSF Scorecard checks."
        ),
    ),
    Control(
        id="C-015",
        name="CodeQL static analysis",
        assets=["A-01", "A-08"],
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
        assets=["A-04"],
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
        assets=["A-04", "A-07"],
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
        assets=["A-08", "A-05"],
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
        assets=["A-04"],
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
        assets=["A-08", "A-04"],
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
            "``slsa-framework/source-actions/slsa_with_provenance`` on every push to ``main``.  "
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
        assets=["A-01", "A-02", "A-04"],
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
        assets=["A-01", "A-04"],
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
    "A-02",
    "A-03",
    "A-04",
    "A-05",
    "A-06",
    "A-07",
    "A-08",
    "A-08b",
}
ASSET_CONTROLS: dict[str, list[Control]] = build_asset_controls_index(
    CONTROLS, _SUPPLY_CHAIN_ASSET_IDS
)

if __name__ == "__main__":
    run_model(build_model, CONTROLS)
