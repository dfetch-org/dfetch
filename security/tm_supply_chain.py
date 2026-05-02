"""Supply-chain threat model for dfetch.

Scope: pre-install lifecycle — code contribution, CI/CD, build
(wheel / sdist), PyPI distribution, and consumer installation.
The installed dfetch package is the handoff point to ``tm_usage.py``.

Run::

    python -m security.tm_supply_chain --dfd
    python -m security.tm_supply_chain --seq
    python -m security.tm_supply_chain --report
"""

import os
import sys

# Ensure the security package is importable when loaded by Sphinx directive
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from pytm import (  # noqa: E402, pylint: disable=import-error,wrong-import-position
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

from security.tm_common import (  # noqa: E402, pylint: disable=wrong-import-position
    THREATS_FILE,
    Control,
    build_asset_controls_index,
    make_dev_env_boundary,
    make_network_boundary,
    make_supply_chain_assumptions,
)

# ── Threat model metadata ────────────────────────────────────────────────────

TM.reset()

tm = TM(
    "dfetch Supply Chain",
    description=(
        "EN 18031 / CRA supply-chain threat model for dfetch.  "
        "Covers the pre-install lifecycle: code contribution, CI/CD, "
        "build (wheel / sdist), PyPI distribution, and consumer installation.  "
        "The installed dfetch package is the handoff point to tm_usage.py."
    ),
    isOrdered=True,
    mergeResponses=True,
    threatsFile=THREATS_FILE,
)

tm.assumptions = make_supply_chain_assumptions()

# ── Trust boundaries ─────────────────────────────────────────────────────────

boundary_dev_env = make_dev_env_boundary()

boundary_github = Boundary("GitHub Actions Infrastructure")
boundary_github.description = (
    "Microsoft-operated ephemeral runners executing the CI/CD workflows.  "
    "Egress traffic is blocked (``harden-runner`` with ``egress-policy: block``) "
    "with an allowlist of permitted endpoints; secrets are propagated via "
    "``secrets: inherit`` in ``ci.yml``."
)

boundary_pypi = Boundary("PyPI / TestPyPI")
boundary_pypi.description = (
    "Python Package Index and its staging registry.  dfetch publishes via "
    "OIDC trusted publishing — no long-lived API token stored."
)

boundary_network = make_network_boundary()

# ── Actors ───────────────────────────────────────────────────────────────────

developer = Actor("Developer")
developer.inBoundary = boundary_dev_env
developer.description = (
    "dfetch project contributor: writes code, reviews PRs, cuts releases.  "
    "Trusted at workstation time; responsible for correct branch-protection "
    "and release workflow configuration."
)

contributor = Actor("Contributor / Attacker")
contributor.inBoundary = boundary_network
contributor.description = (
    "External contributor submitting pull requests, or an adversary attempting "
    "supply-chain manipulation (malicious PR, action-poisoning, or MITM on CI "
    "network traffic).  Code review, branch protection, and SHA-pinned Actions "
    "are the primary controls at this boundary."
)

consumer = Actor("Consumer / End User")
consumer.inBoundary = boundary_dev_env
consumer.description = (
    "Installs dfetch from PyPI (``pip install dfetch``) and invokes it on a "
    "developer workstation or in a CI pipeline.  Trusts PyPI package integrity "
    "and build provenance; currently has no mechanism to verify SLSA attestation "
    "or Sigstore signature for dfetch itself."
)

# ── External entities ────────────────────────────────────────────────────────

gh_repository = ExternalEntity("EA-03: GitHub Repository")
gh_repository.inBoundary = boundary_github
gh_repository.classification = Classification.RESTRICTED
gh_repository.description = (
    "Source code, PRs, releases, and workflow definitions.  "
    "GitHub Actions workflows (``.github/workflows/``) with "
    "``contents:write`` permission can modify repository state and trigger releases."
)

gh_actions_runner = ExternalEntity("EA-04: GitHub Actions Infrastructure")
gh_actions_runner.inBoundary = boundary_github
gh_actions_runner.classification = Classification.RESTRICTED
gh_actions_runner.description = (
    "Microsoft-operated ephemeral runner executing CI/CD workflows.  "
    "Egress policy is ``audit`` (not ``block``) — exfiltration of secrets is "
    "possible if any workflow step is compromised."
)

pypi = ExternalEntity("EA-05: PyPI / TestPyPI")
pypi.inBoundary = boundary_pypi
pypi.classification = Classification.PUBLIC
pypi.description = (
    "Python Package Index.  dfetch is published via OIDC trusted publishing "
    "(no long-lived API token).  Account takeover or registry compromise "
    "would affect every consumer installing dfetch."
)

# ── Processes ────────────────────────────────────────────────────────────────

gh_actions_workflow = Process("GitHub Actions Workflow")
gh_actions_workflow.inBoundary = boundary_github
gh_actions_workflow.description = (
    "CI/CD pipelines: test, build (wheel/msi/deb/rpm), lint, CodeQL, Scorecard, "
    "dependency-review, docs, release.  "
    "All actions pinned by commit SHA.  "
    "harden-runner used in every workflow (egress: audit only)."
)
gh_actions_workflow.controls.isHardened = (
    True  # SHA-pinned actions, persist-credentials:false
)
gh_actions_workflow.controls.providesIntegrity = (
    True  # CodeQL + Scorecard + dependency-review
)
gh_actions_workflow.controls.hasAccessControl = True  # minimal permissions per workflow

python_build = Process("Python Build (wheel / sdist)")
python_build.inBoundary = boundary_github
python_build.description = (
    "Runs ``python -m build`` to produce wheel and sdist.  "
    "Build deps (setuptools, build, fpm, gem) fetched from PyPI/RubyGems without "
    "hash pinning.  SLSA provenance attestations are generated by the release "
    "workflow."
)

# ── PRIMARY ASSETS ───────────────────────────────────────────────────────────

pypi_package = Datastore("PA-04: dfetch PyPI Package")
pypi_package.inBoundary = boundary_pypi
pypi_package.description = (
    "Published wheel and sdist on PyPI (https://pypi.org/project/dfetch/).  "
    "Published via OIDC trusted publishing — no long-lived API token stored.  "
    "A machine-readable CycloneDX SBOM is generated during the build and "
    "published alongside the release.  "
    "Compromise of the PyPI account or registry affects every consumer."
)
pypi_package.storesSensitiveData = False
pypi_package.hasWriteAccess = True  # publish pipeline writes new releases
pypi_package.isSQL = False
pypi_package.classification = Classification.SENSITIVE
pypi_package.controls.usesCodeSigning = False  # no Sigstore/cosign signing

# ── SUPPORTING ASSETS ────────────────────────────────────────────────────────

gh_workflows = Datastore("SA-06: GitHub Actions Workflows")
gh_workflows.inBoundary = boundary_github
gh_workflows.description = (
    "``.github/workflows/*.yml`` — CI/CD configuration checked into the repository.  "
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

oidc_identity = Data(
    "SA-07: PyPI OIDC Identity",
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

dfetch_dev_deps = Datastore("SA-09: dfetch Build / Dev Dependencies")
dfetch_dev_deps.inBoundary = boundary_github
dfetch_dev_deps.description = (
    "Python packages installed during CI: setuptools, build, pylint, bandit, "
    "mypy, pytest, etc.  Ruby gem ``fpm`` for platform builds.  "
    "CRITICAL GAP: installed via ``pip install .`` and "
    "``pip install --upgrade pip build`` without ``--require-hashes``.  "
    "A compromised PyPI mirror or BGP hijack can substitute malicious build tools.  "
    "``gem install fpm`` and ``choco install svn/zig`` are also not hash-verified."
)
dfetch_dev_deps.storesSensitiveData = False
dfetch_dev_deps.hasWriteAccess = False
dfetch_dev_deps.isSQL = False
dfetch_dev_deps.classification = Classification.RESTRICTED

scorecard_results = Datastore("SA-10: OpenSSF Scorecard Results")
scorecard_results.inBoundary = boundary_github
scorecard_results.description = (
    "Weekly OSSF Scorecard SARIF results uploaded to GitHub Code Scanning.  "
    "Covers: branch-protection, CI-tests, code-review, maintained, packaging, "
    "pinned-dependencies, SAST, signed-releases, token-permissions, vulnerabilities, "
    "dangerous-workflow, binary-artifacts, fuzzing, license, CII-best-practices, "
    "security-policy, webhooks.  "
    "Suppression or forgery hides supply-chain regressions."
)
scorecard_results.storesSensitiveData = False
scorecard_results.hasWriteAccess = False
scorecard_results.isSQL = False
scorecard_results.classification = Classification.RESTRICTED

# ── DATA FLOWS ───────────────────────────────────────────────────────────────

df11 = Dataflow(contributor, gh_repository, "DF-11: Submit pull request")
df11.description = (
    "External contributor opens a PR against the dfetch repository.  "
    "Workflow files in ``.github/workflows/`` can be modified by PRs.  "
    "``ci.yml`` only passes required repository secrets to the test and docs "
    "workflows, preventing malicious PR steps from exfiltrating secrets."
)
df11.protocol = "HTTPS"
df11.controls.hasAccessControl = True

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
    "SBOM attestations with Sigstore signatures are generated by the release pipeline."
)
df13.protocol = "HTTPS"
df13.controls.isEncrypted = True
df13.controls.usesCodeSigning = True  # SBOM attestation via actions/attest

df14 = Dataflow(consumer, pypi, "DF-14: pip install dfetch")
df14.description = (
    "Consumer installs dfetch from PyPI.  The installed wheel contains the dfetch "
    "CLI; the handoff to the runtime-usage model occurs when the consumer invokes "
    "dfetch with a manifest."
)
df14.protocol = "HTTPS"
df14.controls.isEncrypted = True

# ── CONTROLS AND GAPS ────────────────────────────────────────────────────────

CONTROLS: list[Control] = [
    # ── Implemented controls ─────────────────────────────────────────────────
    Control(
        id="C-009",
        name="Actions commit-SHA pinning",
        assets=["SA-06", "EA-04"],
        threats=["DFT-07"],
        description=(
            "Every third-party GitHub Action is pinned to a full commit SHA, "
            "preventing tag-mutable supply-chain substitution."
        ),
        reference=".github/workflows/*.yml",
    ),
    Control(
        id="C-010",
        name="OIDC trusted publishing",
        assets=["SA-07", "PA-04"],
        threats=["DFT-07"],
        description=(
            "PyPI publishes via ``pypa/gh-action-pypi-publish`` with "
            "``id-token: write`` and no stored long-lived API token."
        ),
        reference=".github/workflows/python-publish.yml",
    ),
    Control(
        id="C-011",
        name="Minimal workflow permissions",
        assets=["SA-06"],
        threats=["DFT-07"],
        description=(
            "Each workflow declares only the permissions it requires "
            "(default ``contents: read``)."
        ),
        reference=".github/workflows/*.yml",
    ),
    Control(
        id="C-012",
        name="persist-credentials: false",
        assets=["SA-02", "EA-03"],
        threats=["DFT-07"],
        description=(
            "All ``actions/checkout`` steps drop the GitHub token from the "
            "working tree after checkout."
        ),
        reference=".github/workflows/*.yml",
    ),
    Control(
        id="C-013",
        name="Harden-runner (egress block)",
        assets=["SA-02", "EA-04"],
        threats=["DFT-07"],
        description=(
            "``step-security/harden-runner`` is used in every workflow with "
            "``egress-policy: block`` and an allowlist of permitted endpoints.  "
            "All non-allowlisted outbound connections are blocked."
        ),
        reference=".github/workflows/*.yml",
    ),
    Control(
        id="C-014",
        name="OpenSSF Scorecard",
        assets=["EA-03", "SA-10"],
        threats=["DFT-07", "DFT-10"],
        description=(
            "Weekly OSSF Scorecard analysis uploaded to GitHub Code Scanning "
            "covers the full set of OpenSSF Scorecard checks."
        ),
        reference=".github/workflows/scorecard.yml",
    ),
    Control(
        id="C-015",
        name="CodeQL static analysis",
        assets=["SA-01", "SA-06"],
        threats=["DFT-03", "DFT-06"],
        description=(
            "CodeQL scans the Python codebase for security vulnerabilities on "
            "every push and pull request."
        ),
        reference=".github/workflows/codeql-analysis.yml",
    ),
    Control(
        id="C-016",
        name="Dependency review",
        assets=["SA-09"],
        threats=["DFT-10"],
        description=(
            "``actions/dependency-review-action`` checks for known vulnerabilities "
            "in newly added dependencies on every pull request."
        ),
        reference=".github/workflows/dependency-review.yml",
    ),
    Control(
        id="C-017",
        name="bandit security linter",
        assets=["SA-01"],
        threats=["DFT-03", "DFT-06"],
        description=(
            "``bandit -r dfetch`` runs in CI to detect common Python security issues."
        ),
        reference="pyproject.toml",
    ),
    Control(
        id="C-021",
        name="Sigstore SBOM attestation",
        assets=["PA-04"],
        threats=["DFT-05"],
        description=(
            "The release pipeline generates CycloneDX SBOM attestations via "
            "``actions/attest`` with Sigstore signatures.  These attest the build "
            "provenance for the published packages."
        ),
    ),
    Control(
        id="C-022",
        name="CycloneDX SBOM on PyPI",
        assets=["PA-04", "PA-05"],
        threats=["DFT-02"],
        description=(
            "A CycloneDX SBOM is generated during the build and published "
            "alongside the PyPI release, satisfying CRA Article 13 requirements."
        ),
    ),
    Control(
        id="C-024",
        name="``secrets: inherit`` scope",
        assets=["SA-06", "SA-02"],
        threats=["DFT-07"],
        description=(
            "``ci.yml`` only passes required repository secrets to the test and "
            "docs workflows, preventing malicious PR steps from exfiltrating "
            "unrelated secrets."
        ),
    ),
    Control(
        id="C-025",
        name="Harden-runner in block mode",
        assets=["EA-04", "SA-06"],
        threats=["DFT-07"],
        description=(
            "``step-security/harden-runner`` is configured with "
            "``egress-policy: block`` and an allowlist of permitted endpoints.  "
            "Non-allowlisted outbound connections are blocked."
        ),
    ),
    # ── Gaps ─────────────────────────────────────────────────────────────────
    Control(
        id="C-023",
        name="Build deps without hash pinning",
        assets=["SA-09"],
        threats=["DFT-10"],
        status="gap",
        description=(
            "``pip install .`` and ``pip install --upgrade pip build`` in CI do not "
            "use ``--require-hashes``.  A compromised PyPI mirror can substitute "
            "malicious build tooling."
        ),
    ),
]

ASSET_CONTROLS: dict[str, list[Control]] = build_asset_controls_index(CONTROLS)

if __name__ == "__main__":
    tm.process()
