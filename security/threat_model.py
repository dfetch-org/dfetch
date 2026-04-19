"""CRA / EN 18031 threat model for dfetch — Phase 1: asset register.

Covers the full SDLC: development, CI/CD (GitHub Actions), distribution
(PyPI), and runtime (developer / embedded-build environment).

Run:
    python -m security.threat_model --dfd        # Graphviz DFD
    python -m security.threat_model --seq        # sequence diagram (stdout)
    python -m security.threat_model --report     # STRIDE findings report
"""

from pytm import (
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

# ── Threat model metadata ────────────────────────────────────────────────────

TM.reset()

tm = TM(
    "dfetch",
    description=(
        "EN 18031 / CRA threat model for dfetch — a supply-chain vendoring tool "
        "that fetches external source-code dependencies (Git, SVN, archive) and "
        "copies them as plain files into a project. "
        "Scope: full SDLC from source contribution through CI/CD, PyPI "
        "distribution, and runtime execution in developer/CI environments."
    ),
    threatsFile=None,
    isOrdered=True,
    mergeResponses=True,
)

tm.assumptions = [
    "Developer workstations are trusted at dfetch invocation time.",
    "TLS certificate validation is delegated to the OS / git / SVN client.",
    "No runtime secrets are persisted to disk by dfetch itself.",
    "GitHub Actions environments inherit the security posture of the GitHub-hosted runner.",
    "The integrity.hash field in the manifest is OPTIONAL — archive deps without it have "
    "no content-authenticity guarantee beyond TLS transport (which itself is absent for "
    "http:// URLs).",
    "Branch/tag-pinned Git deps are mutable references — upstream history rewrites or "
    "force-pushes silently change what is fetched without triggering a manifest diff.",
    "harden-runner egress policy is set to 'audit', not 'block' — outbound network "
    "connections from CI runners are logged but not prevented.",
    "dfetch's own build/dev dependencies (pip install .) are not installed with "
    "--require-hashes, so a compromised PyPI mirror can substitute packages.",
]

# ── Trust boundaries ─────────────────────────────────────────────────────────

boundary_dev_env = Boundary("Local Developer Environment")
boundary_github = Boundary("GitHub Actions Infrastructure")
boundary_network = Boundary("Internet")
boundary_remote_vcs = Boundary("Remote VCS Infrastructure")
boundary_pypi = Boundary("PyPI / TestPyPI")
boundary_archive = Boundary("Archive Content Space")

# ── Actors ───────────────────────────────────────────────────────────────────

developer = Actor("Developer")
developer.inBoundary = boundary_dev_env

contributor = Actor("Contributor / Attacker")
contributor.inBoundary = boundary_network

consumer = Actor("Consumer / End User")
consumer.inBoundary = boundary_dev_env

# ── External entities ────────────────────────────────────────────────────────

remote_git_svn = ExternalEntity("EA-01: Remote VCS Server")
remote_git_svn.inBoundary = boundary_remote_vcs
remote_git_svn.description = (
    "Upstream Git or SVN host: GitHub, GitLab, Gitea, self-hosted Git/SVN. "
    "Not controlled by the dfetch project; content is untrusted until verified."
)

archive_server = ExternalEntity("EA-02: Archive HTTP Server")
archive_server.inBoundary = boundary_remote_vcs
archive_server.description = (
    "HTTP/HTTPS server serving .tar.gz, .tgz, .tar.bz2, .tar.xz, or .zip files. "
    "CRITICAL: http:// (non-TLS) URLs are accepted without enforcement of integrity "
    "hashes — the integrity.hash field is optional."
)

gh_actions_runner = ExternalEntity("EA-04: GitHub Actions Runner")
gh_actions_runner.inBoundary = boundary_github
gh_actions_runner.description = (
    "Microsoft-operated ephemeral runner executing CI/CD workflows. "
    "Egress policy is 'audit' (not 'block') — exfiltration of secrets is possible "
    "if any workflow step is compromised."
)

gh_repository = ExternalEntity("EA-03: GitHub Repository")
gh_repository.inBoundary = boundary_github
gh_repository.description = (
    "Source code, PRs, releases, and workflow definitions. "
    "GitHub Actions workflows (.github/workflows/) with contents:write permission "
    "can modify repository state and trigger releases."
)

pypi = ExternalEntity("EA-05: PyPI / TestPyPI")
pypi.inBoundary = boundary_pypi
pypi.description = (
    "Python Package Index. dfetch is published via OIDC trusted publishing "
    "(no long-lived API token). Account takeover or registry compromise "
    "would affect every consumer installing dfetch."
)

consumer_build = ExternalEntity("EA-07: Consumer Build System")
consumer_build.inBoundary = boundary_dev_env
consumer_build.description = (
    "Build system that compiles fetched source code (PA-02). "
    "Not controlled by dfetch — it receives untrusted third-party source."
)

# ── Processes ────────────────────────────────────────────────────────────────

dfetch_cli = Process("SA-01: dfetch CLI")
dfetch_cli.inBoundary = boundary_dev_env
dfetch_cli.description = (
    "Python CLI entry point dispatching to: update, check, diff, add, remove, "
    "patch, format-patch, freeze, import, report, validate, environment. "
    "Invokes Git and SVN as subprocesses (shell=False, list args). "
    "Extracts archives with decompression-bomb limits and path-traversal checks."
)
dfetch_cli.controls.validatesInput = True  # StrictYAML + SAFE_STR regex
dfetch_cli.controls.sanitizesInput = True  # check_no_path_traversal realpath-based
dfetch_cli.controls.usesParameterizedInput = (
    True  # shell=False, list-based subprocesses
)
dfetch_cli.controls.checksInputBounds = True  # 500MB / 10k-member archive limits
dfetch_cli.controls.isHardened = True  # BatchMode=yes, --non-interactive, type checks
dfetch_cli.controls.providesIntegrity = True  # hmac.compare_digest SHA-256/384/512

gh_actions_workflow = Process("GitHub Actions Workflow")
gh_actions_workflow.inBoundary = boundary_github
gh_actions_workflow.description = (
    "CI/CD pipelines: test, build (wheel/msi/deb/rpm), lint, CodeQL, Scorecard, "
    "dependency-review, docs, release. "
    "All actions pinned by commit SHA. "
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
    "Runs 'python -m build' to produce wheel and sdist. "
    "MISSING: no SLSA provenance attestation generated. "
    "MISSING: pip install steps do not use --require-hashes. "
    "Build deps (setuptools, build, fpm, gem) fetched from PyPI/RubyGems without hash pinning."
)

# ── PRIMARY ASSETS ───────────────────────────────────────────────────────────
#
# PA-01 … PA-05: assets with direct business/security value whose compromise
# causes direct harm to the dfetch project or its consumers.

manifest_store = Datastore("PA-01: dfetch Manifest")
manifest_store.inBoundary = boundary_dev_env
manifest_store.description = (
    "dfetch.yaml — declares all upstream sources (URL/VCS type), version pins "
    "(branch / tag / revision / SHA), dst paths, patch references, and optional "
    "integrity hashes. "
    "Tampering redirects fetches to attacker-controlled sources. "
    "RISK: integrity.hash is Optional in schema — archive deps can be declared "
    "without any content-authenticity guarantee."
)
manifest_store.storesSensitiveData = True
manifest_store.hasWriteAccess = True
manifest_store.isSQL = False
manifest_store.classification = Classification.SENSITIVE
manifest_store.controls.isEncryptedAtRest = False
manifest_store.controls.validatesInput = True  # StrictYAML validation on read

fetched_source = Datastore("PA-02: Fetched Source Code")
fetched_source.inBoundary = boundary_dev_env
fetched_source.description = (
    "Third-party source code written to the dst: path after extraction / checkout. "
    "Becomes a direct build input for the consuming project. "
    "A compromised upstream or MITM can inject malicious code that executes in the "
    "consumer's build system, test runner, or production binary."
)
fetched_source.storesSensitiveData = True
fetched_source.hasWriteAccess = True
fetched_source.isSQL = False
fetched_source.classification = Classification.SENSITIVE
fetched_source.controls.isEncryptedAtRest = False

integrity_hash_record = Datastore("PA-03: Integrity Hash Record")
integrity_hash_record.inBoundary = boundary_dev_env
integrity_hash_record.description = (
    "integrity.hash: field in dfetch.yaml (sha256/sha384/sha512:<hex>). "
    "The sole trust anchor for archive-type dependencies. "
    "Verified via hmac.compare_digest (constant-time). "
    "CRITICAL GAP: field is Optional — absence disables all content verification. "
    "CRITICAL GAP: Git and SVN deps have NO equivalent integrity mechanism; "
    "authenticity relies entirely on transport security (TLS/SSH)."
)
integrity_hash_record.storesSensitiveData = False
integrity_hash_record.hasWriteAccess = (
    True  # developers and processes write this field in dfetch.yaml
)
integrity_hash_record.classification = Classification.SENSITIVE
integrity_hash_record.controls.providesIntegrity = True

pypi_package = Datastore("PA-04: dfetch PyPI Package")
pypi_package.inBoundary = boundary_pypi
pypi_package.description = (
    "Published wheel and sdist on PyPI (https://pypi.org/project/dfetch/). "
    "Published via OIDC trusted publishing — no long-lived API token stored. "
    "MISSING: no SLSA provenance attestation or Sigstore signature. "
    "Compromise of the PyPI account or registry affects every consumer."
)
pypi_package.storesSensitiveData = False
pypi_package.hasWriteAccess = (
    True  # publish pipeline writes new releases to this package
)
pypi_package.classification = Classification.SENSITIVE
pypi_package.controls.usesCodeSigning = False  # no Sigstore/cosign signing

sbom_output = Datastore("PA-05: SBOM Output (CycloneDX)")
sbom_output.inBoundary = boundary_dev_env
sbom_output.description = (
    "CycloneDX JSON/XML produced by 'dfetch report -t sbom'. "
    "Enumerates vendored components with PURL, license, and hash. "
    "Falsification hides actual dependencies from downstream CVE scanners. "
    "NOTE: this SBOM covers vendored deps only — dfetch itself has no machine-readable "
    "SBOM on PyPI (CRA requires SBOM for the distributed product)."
)
sbom_output.storesSensitiveData = False
sbom_output.hasWriteAccess = True
sbom_output.classification = Classification.RESTRICTED

# ── SUPPORTING ASSETS ────────────────────────────────────────────────────────
#
# SA-01 … SA-10: assets that enable primary assets; their loss degrades
# security or availability of primary assets.

vcs_credentials = Data(
    "SA-02: VCS Credentials",
    description=(
        "SSH private keys, HTTPS Personal Access Tokens, SVN passwords. "
        "Used to authenticate to private upstream repositories. "
        "dfetch never persists these — managed by OS keychain or CI secret store. "
        "Exfiltration via a compromised CI workflow step is the primary risk "
        "(harden-runner is in audit mode, not block mode)."
    ),
    classification=Classification.SECRET,
    isCredentials=True,
    isPII=False,
    isStored=False,
    isDestEncryptedAtRest=False,
    isSourceEncryptedAtRest=True,
)

metadata_store = Datastore("SA-03: Dependency Metadata")
metadata_store.inBoundary = boundary_dev_env
metadata_store.description = (
    ".dfetch_data.yaml files written after each successful fetch. "
    "Contains: remote_url, revision/branch/tag, hash, last-fetch timestamp. "
    "Read by 'dfetch check' to detect outdated deps. "
    "Tampering can suppress update notifications — an attacker who controls the "
    "local filesystem can silently mask a compromised vendored dep."
)
metadata_store.storesSensitiveData = False
metadata_store.hasWriteAccess = True
metadata_store.classification = Classification.RESTRICTED

patch_store = Datastore("SA-04: Patch Files")
patch_store.inBoundary = boundary_dev_env
patch_store.description = (
    "Unified-diff .patch files referenced by patch: in dfetch.yaml. "
    "Applied by patch-ng after fetch. "
    "A malicious patch can write to arbitrary destination paths — "
    "dfetch's path-traversal guards apply to archive extraction but patch-ng's "
    "own path safety depends on its internal implementation. "
    "Patch files are not integrity-verified (no hash in manifest schema)."
)
patch_store.storesSensitiveData = False
patch_store.hasWriteAccess = True
patch_store.classification = Classification.RESTRICTED

local_vcs_cache = Datastore("SA-05: Local VCS Cache (temp)")
local_vcs_cache.inBoundary = boundary_dev_env
local_vcs_cache.description = (
    "Temporary directory used during git-clone / svn-checkout / archive extraction. "
    "Deleted after content is copied to dst. "
    "Path-traversal attacks targeting this space are mitigated by "
    "check_no_path_traversal() and post-extraction symlink walks."
)
local_vcs_cache.storesSensitiveData = False
local_vcs_cache.hasWriteAccess = True
local_vcs_cache.classification = Classification.RESTRICTED

gh_workflows = Datastore("SA-06: GitHub Actions Workflows")
gh_workflows.inBoundary = boundary_github
gh_workflows.description = (
    ".github/workflows/*.yml — CI/CD configuration checked into the repository. "
    "11 workflows: ci, build, run, test, docs, release, python-publish, "
    "dependency-review, codeql-analysis, scorecard, devcontainer. "
    "A malicious PR that modifies workflows can exfiltrate secrets or publish "
    "a backdoored release. "
    "Mitigated by: SHA-pinned actions, persist-credentials:false, minimal permissions. "
    "RISK: 'secrets: inherit' in ci.yml propagates ALL secrets to test and docs workflows."
)
gh_workflows.storesSensitiveData = False
gh_workflows.hasWriteAccess = False
gh_workflows.classification = Classification.RESTRICTED
gh_workflows.controls.isHardened = True

oidc_identity = Data(
    "SA-07: PyPI OIDC Identity",
    description=(
        "GitHub OIDC token exchanged for a short-lived PyPI publish credential. "
        "No long-lived API token stored — this is a significant security improvement. "
        "The token is scoped to the GitHub Actions environment named 'pypi'. "
        "Risk: if the GitHub OIDC issuer or the PyPI trusted-publisher mapping is "
        "misconfigured, an attacker could mint a valid publish token."
    ),
    classification=Classification.SECRET,
    isCredentials=True,
    isPII=False,
    isStored=False,
    isDestEncryptedAtRest=False,
    isSourceEncryptedAtRest=True,
)

audit_reports = Datastore("SA-08: Audit / Check Reports")
audit_reports.inBoundary = boundary_dev_env
audit_reports.description = (
    "SARIF, Jenkins warnings-ng, Code Climate JSON produced by 'dfetch check'. "
    "Falsification hides vulnerabilities from downstream security dashboards. "
    "Also includes CodeQL and OpenSSF Scorecard results uploaded to GitHub."
)
audit_reports.storesSensitiveData = False
audit_reports.hasWriteAccess = True
audit_reports.classification = Classification.RESTRICTED

dfetch_dev_deps = Datastore("SA-09: dfetch Build / Dev Dependencies")
dfetch_dev_deps.inBoundary = boundary_github
dfetch_dev_deps.description = (
    "Python packages installed during CI: setuptools, build, pylint, bandit, "
    "mypy, pytest, etc. Ruby gem 'fpm' for platform builds. "
    "CRITICAL GAP: installed via 'pip install .' and 'pip install --upgrade pip build' "
    "without --require-hashes. A compromised PyPI mirror or BGP hijack can substitute "
    "malicious build tools — this is a first-order supply-chain risk for dfetch's own "
    "release pipeline. "
    "Similarly, 'gem install fpm' and 'choco install svn/zig' are not hash-verified."
)
dfetch_dev_deps.storesSensitiveData = False
dfetch_dev_deps.hasWriteAccess = False
dfetch_dev_deps.classification = Classification.RESTRICTED

scorecard_results = Datastore("SA-10: OpenSSF Scorecard Results")
scorecard_results.inBoundary = boundary_github
scorecard_results.description = (
    "Weekly OSSF Scorecard SARIF results uploaded to GitHub Code Scanning. "
    "Covers: branch-protection, CI-tests, code-review, maintained, "
    "packaging, pinned-dependencies, SAST, signed-releases, token-permissions, "
    "vulnerabilities, dangerous-workflow, binary-artifacts, fuzzing, license, "
    "CII-best-practices, security-policy, webhooks. "
    "Suppression or forgery hides supply-chain regressions."
)
scorecard_results.storesSensitiveData = False
scorecard_results.hasWriteAccess = False
scorecard_results.classification = Classification.RESTRICTED

# ── ENVIRONMENTAL ASSETS ─────────────────────────────────────────────────────
#
# EA-01 … EA-08: infrastructure the system depends on.

# EA-01: Remote VCS Servers — modelled as remote_git_svn (ExternalEntity above)
# EA-02: Archive HTTP Servers — modelled as archive_server (ExternalEntity above)
# EA-03: GitHub Repository — modelled as gh_repository (ExternalEntity above)
# EA-04: GitHub Actions Infrastructure — modelled as gh_actions_runner (ExternalEntity above)
# EA-05: PyPI / TestPyPI — modelled as pypi (ExternalEntity above)
# EA-06: Developer Workstation / CI Runner — modelled as developer / gh_actions_runner (Actors/ExternalEntity above)
# EA-07: Consumer Build System — modelled as consumer_build (ExternalEntity above)
# EA-08: Network Transport — modelled as boundary_network (Boundary above); symbol: network_transport

# ── DATA FLOWS ───────────────────────────────────────────────────────────────
#
# DF-01 … DF-15: annotated with controls reflecting existing implementation.

df01 = Dataflow(developer, dfetch_cli, "DF-01: Invoke dfetch command")
df01.description = "CLI invocation: update / check / diff / report / add etc."

df02 = Dataflow(manifest_store, dfetch_cli, "DF-02: Read manifest")
df02.description = "StrictYAML parse; SAFE_STR regex rejects control characters."
df02.controls.validatesInput = True

df03 = Dataflow(dfetch_cli, remote_git_svn, "DF-03: Fetch VCS content (outbound)")
df03.description = (
    "git fetch / git ls-remote / svn ls / svn info outbound. "
    "HTTPS uses redirect following (max 10). SSH uses BatchMode=yes. "
    "RISK: svn:// and http:// (non-TLS) protocols are accepted by dfetch; "
    "no protocol enforcement in manifest schema."
)
df03.protocol = "HTTPS / SSH / svn"
df03.controls.isEncrypted = True  # for HTTPS/SSH paths; NOT for svn:// or http://
df03.controls.isHardened = True  # BatchMode=yes, --non-interactive

df04 = Dataflow(remote_git_svn, dfetch_cli, "DF-04: VCS content (inbound, untrusted)")
df04.description = (
    "Repository tree / file content arriving from upstream VCS. "
    "No integrity verification for Git or SVN content beyond transport security. "
    "Content is controlled by the upstream repository owner."
)
df04.protocol = "HTTPS / SSH / svn"
df04.controls.isEncrypted = True
df04.controls.providesIntegrity = False  # no end-to-end hash for git/svn content

df05 = Dataflow(dfetch_cli, archive_server, "DF-05: Archive download request")
df05.description = (
    "HTTP GET to archive URL. Follows up to 10 3xx redirects. "
    "RISK: http:// (non-TLS) URLs accepted — request and response are unencrypted."
)
df05.protocol = "HTTP or HTTPS"
df05.controls.isEncrypted = False  # not guaranteed; http:// accepted

df06 = Dataflow(archive_server, dfetch_cli, "DF-06: Archive bytes (untrusted)")
df06.description = (
    "Raw archive bytes streamed into dfetch. "
    "Hash computed in-flight when integrity.hash is specified. "
    "CRITICAL: when integrity.hash is absent, no content verification occurs."
)
df06.protocol = "HTTP or HTTPS"
df06.controls.providesIntegrity = False  # hash is optional; may be absent
df06.controls.isEncrypted = False  # http:// allowed

df07 = Dataflow(dfetch_cli, fetched_source, "DF-07: Write vendored files")
df07.description = (
    "Post-validation copy to dst path. Path-traversal checked via "
    "check_no_path_traversal(). Symlinks validated post-extraction."
)
df07.controls.sanitizesInput = True
df07.controls.providesIntegrity = True

df08 = Dataflow(dfetch_cli, metadata_store, "DF-08: Write dependency metadata")
df08.description = "Writes .dfetch_data.yaml tracking remote_url, revision, hash."

df09 = Dataflow(dfetch_cli, sbom_output, "DF-09: Write SBOM")
df09.description = "CycloneDX BOM generation from metadata store contents."

df10 = Dataflow(patch_store, dfetch_cli, "DF-10: Read and apply patch")
df10.description = (
    "patch-ng reads unified-diff file and applies to vendor directory. "
    "RISK: patch files are not integrity-verified (no hash in manifest schema). "
    "patch-ng path safety depends on its own internal implementation."
)
df10.controls.validatesInput = False  # no integrity hash on patch files

df11 = Dataflow(contributor, gh_repository, "DF-11: Submit pull request")
df11.description = (
    "External contributor opens a PR against the dfetch repository. "
    "Workflow files in .github/workflows/ can be modified by PRs. "
    "RISK: 'secrets: inherit' in ci.yml propagates secrets to test+docs workflows "
    "triggered on PR — a malicious PR step could exfiltrate secrets."
)
df11.protocol = "HTTPS"
df11.controls.hasAccessControl = True

df12 = Dataflow(gh_actions_runner, gh_repository, "DF-12: CI checkout and build")
df12.description = (
    "GitHub Actions checks out source, installs deps, runs tests, lints, builds. "
    "persist-credentials:false on all checkout steps. "
    "All third-party actions pinned by commit SHA."
)
df12.controls.isHardened = True
df12.controls.providesIntegrity = True

df13 = Dataflow(gh_actions_runner, pypi, "DF-13: Publish to PyPI (OIDC)")
df13.description = (
    "On release event, wheel/sdist uploaded to PyPI via pypa/gh-action-pypi-publish. "
    "OIDC trusted publishing: no stored API token. "
    "MISSING: no SLSA provenance attestation, no Sigstore/cosign package signing."
)
df13.protocol = "HTTPS"
df13.controls.isEncrypted = True
df13.controls.usesCodeSigning = False  # no Sigstore signing

df14 = Dataflow(consumer, pypi, "DF-14: pip install dfetch")
df14.description = "Consumer installs dfetch from PyPI."
df14.protocol = "HTTPS"
df14.controls.isEncrypted = True

df15 = Dataflow(pypi_package, consumer_build, "DF-15: Installed dfetch")
df15.description = (
    "Installed dfetch wheel executed in consumer environment. "
    "Consumer cannot verify build provenance without SLSA attestation."
)

if __name__ == "__main__":
    tm.process()
