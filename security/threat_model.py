"""CRA / EN 18031 threat model for dfetch — Phase 1: asset register.

Covers the full SDLC: development, CI/CD (GitHub Actions), distribution
(PyPI), and runtime (developer / embedded-build environment).

Run:
    python -m security.threat_model --dfd        # Graphviz DFD
    python -m security.threat_model --seq        # sequence diagram (stdout)
    python -m security.threat_model --report     # STRIDE findings report
"""

from dataclasses import dataclass, field
from typing import Literal

from pytm import (
    TM,
    Actor,
    Assumption,
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
    isOrdered=True,
    mergeResponses=True,
)

tm.assumptions = [
    Assumption(
        "Trusted workstation",
        description=(
            "Developer workstations are trusted at dfetch invocation time.  "
            "A compromised workstation is outside the scope of this threat model."
        ),
    ),
    Assumption(
        "TLS delegated to client",
        description=(
            "TLS certificate validation is delegated to the OS trust store and the "
            "git / svn / urllib clients.  dfetch does not independently validate certificates."
        ),
    ),
    Assumption(
        "No persisted secrets",
        description=(
            "No runtime secrets are persisted to disk by dfetch itself.  "
            "VCS credentials are managed by the OS keychain, SSH agent, or CI secret store."
        ),
    ),
    Assumption(
        "CI runner posture",
        description=(
            "GitHub Actions environments inherit the security posture of the "
            "GitHub-hosted runner.  Ephemeral runner isolation is provided by GitHub."
        ),
    ),
    Assumption(
        "Optional integrity hash",
        description=(
            "The ``integrity.hash`` field in the manifest is optional.  "
            "Archive dependencies without it have no content-authenticity guarantee "
            "beyond TLS transport, which is itself absent for plain ``http://`` URLs."
        ),
    ),
    Assumption(
        "Mutable VCS references",
        description=(
            "Branch- and tag-pinned Git dependencies are mutable references.  "
            "Upstream force-pushes silently change what is fetched without "
            "triggering a manifest diff."
        ),
    ),
    Assumption(
        "Harden-runner in audit mode",
        description=(
            "The ``harden-runner`` egress policy is set to ``audit``, not ``block``.  "
            "Outbound network connections from CI runners are logged but not prevented."
        ),
    ),
    Assumption(
        "Build deps without hash pinning",
        description=(
            "dfetch's own build and dev dependencies are installed without "
            "``--require-hashes``, so a compromised PyPI mirror can substitute packages."
        ),
    ),
]

# ── Trust boundaries ─────────────────────────────────────────────────────────

boundary_dev_env = Boundary("Local Developer Environment")
boundary_dev_env.description = (
    "Developer workstation or local CI runner.  Assumed trusted at invocation time.  "
    "Hosts the manifest (``dfetch.yaml``), vendor directory, dependency metadata "
    "(``.dfetch_data.yaml``), and patch files."
)

boundary_github = Boundary("GitHub Actions Infrastructure")
boundary_github.description = (
    "Microsoft-operated ephemeral runners executing the 11 CI/CD workflows.  "
    "Semi-trusted: egress is audited (``harden-runner``) but not blocked; "
    "secrets are propagated via ``secrets: inherit`` in ``ci.yml``."
)

boundary_network = Boundary("Internet")
boundary_network.description = (
    "All traffic crossing the local/remote boundary.  TLS enforcement is the "
    "responsibility of the OS and VCS clients; dfetch does not enforce HTTPS "
    "on manifest URLs."
)

boundary_remote_vcs = Boundary("Remote VCS Infrastructure")
boundary_remote_vcs.description = (
    "Upstream Git and SVN servers (GitHub, GitLab, Gitea, self-hosted).  "
    "Not controlled by the dfetch project; content is untrusted until verified."
)

boundary_pypi = Boundary("PyPI / TestPyPI")
boundary_pypi.description = (
    "Python Package Index and its staging registry.  dfetch publishes via "
    "OIDC trusted publishing — no long-lived API token stored."
)

boundary_archive = Boundary("Archive Content Space")
boundary_archive.description = (
    "Downloaded archive bytes before extraction and validation.  "
    "Decompression-bomb and path-traversal checks enforce this boundary "
    "during extraction."
)

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
remote_git_svn.classification = Classification.PUBLIC
remote_git_svn.description = (
    "Upstream Git or SVN host: GitHub, GitLab, Gitea, self-hosted Git/SVN. "
    "Not controlled by the dfetch project; content is untrusted until verified."
)

archive_server = ExternalEntity("EA-02: Archive HTTP Server")
archive_server.inBoundary = boundary_remote_vcs
archive_server.classification = Classification.PUBLIC
archive_server.description = (
    "HTTP/HTTPS server serving .tar.gz, .tgz, .tar.bz2, .tar.xz, or .zip files. "
    "CRITICAL: http:// (non-TLS) URLs are accepted without enforcement of integrity "
    "hashes — the integrity.hash field is optional."
)

gh_repository = ExternalEntity("EA-03: GitHub Repository")
gh_repository.inBoundary = boundary_github
gh_repository.classification = Classification.RESTRICTED
gh_repository.description = (
    "Source code, PRs, releases, and workflow definitions. "
    "GitHub Actions workflows (.github/workflows/) with contents:write permission "
    "can modify repository state and trigger releases."
)

gh_actions_runner = ExternalEntity("EA-04: GitHub Actions Infrastructure")
gh_actions_runner.inBoundary = boundary_github
gh_actions_runner.classification = Classification.RESTRICTED
gh_actions_runner.description = (
    "Microsoft-operated ephemeral runner executing CI/CD workflows. "
    "Egress policy is 'audit' (not 'block') — exfiltration of secrets is possible "
    "if any workflow step is compromised."
)

pypi = ExternalEntity("EA-05: PyPI / TestPyPI")
pypi.inBoundary = boundary_pypi
pypi.classification = Classification.PUBLIC
pypi.description = (
    "Python Package Index. dfetch is published via OIDC trusted publishing "
    "(no long-lived API token). Account takeover or registry compromise "
    "would affect every consumer installing dfetch."
)

consumer_build = ExternalEntity("EA-07: Consumer Build System")
consumer_build.inBoundary = boundary_dev_env
consumer_build.classification = Classification.RESTRICTED
consumer_build.description = (
    "Build system that compiles fetched source code (PA-02). "
    "Not controlled by dfetch — it receives untrusted third-party source."
)

# ── Processes ────────────────────────────────────────────────────────────────

dfetch_cli = Process("SA-01: dfetch Process")
dfetch_cli.inBoundary = boundary_dev_env
dfetch_cli.classification = Classification.RESTRICTED
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
gh_workflows.hasWriteAccess = True  # PRs can modify .github/workflows/ definitions
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

df03_tls = Dataflow(dfetch_cli, remote_git_svn, "DF-03a: Fetch VCS content — HTTPS/SSH")
df03_tls.description = (
    "git fetch / git ls-remote over HTTPS or SSH. "
    "HTTPS follows up to 10 redirects. SSH enforces BatchMode=yes and "
    "GIT_TERMINAL_PROMPT=0 (no credential prompts). SVN over svn+https:// or "
    "SSH tunnel. Transport is encrypted and host identity verified."
)
df03_tls.protocol = "HTTPS / SSH"
df03_tls.controls.isEncrypted = True
df03_tls.controls.isHardened = True  # BatchMode=yes, --non-interactive

df03_plain = Dataflow(
    dfetch_cli, remote_git_svn, "DF-03b: Fetch VCS content — svn:// / http://"
)
df03_plain.description = (
    "git fetch over http:// or SVN over svn:// (plain, non-TLS). "
    "dfetch accepts these protocols without enforcement — no TLS check in manifest "
    "schema. Traffic is unencrypted; MITM can substitute repository content or "
    "capture credentials passed over these transports. "
    "RECOMMENDATION: restrict manifest URLs to HTTPS / svn+https:// / SSH."
)
df03_plain.protocol = "http / svn"
df03_plain.controls.isEncrypted = False
df03_plain.controls.isHardened = False

df04_tls = Dataflow(
    remote_git_svn, dfetch_cli, "DF-04a: VCS content inbound — HTTPS/SSH"
)
df04_tls.description = (
    "Repository tree and file content over HTTPS or SSH. Transport is encrypted. "
    "No end-to-end content hash for Git or SVN — authenticity relies on transport "
    "security and upstream repository integrity."
)
df04_tls.protocol = "HTTPS / SSH"
df04_tls.controls.isEncrypted = True
df04_tls.controls.providesIntegrity = False  # no end-to-end hash for git/svn content

df04_plain = Dataflow(
    remote_git_svn, dfetch_cli, "DF-04b: VCS content inbound — svn:// / http://"
)
df04_plain.description = (
    "Repository content over unencrypted http:// or svn://. "
    "A network-positioned attacker can substitute arbitrary content without detection "
    "— there is no transport encryption and no content hash."
)
df04_plain.protocol = "http / svn"
df04_plain.controls.isEncrypted = False
df04_plain.controls.providesIntegrity = False

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
df07.controls.providesIntegrity = (
    False  # integrity is conditional on hash presence (checked in DF-05/DF-06)
)

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

df12 = Dataflow(gh_repository, gh_actions_runner, "DF-12: CI checkout and build")
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

# ── CONTROL DATACLASS ────────────────────────────────────────────────────────


@dataclass
class Control:
    """A security control or an unimplemented gap.

    A gap is simply a control whose ``status`` is ``"gap"`` (or ``"planned"``).
    Both are stored in the same ``CONTROLS`` list and split at render time.
    """

    id: str
    name: str
    description: str
    assets: list[str] = field(default_factory=list)
    status: Literal["implemented", "planned", "gap"] = "implemented"
    reference: str = ""

    def to_pytm(self) -> str:
        """Return a human-readable label for traceability comments and tables."""
        return f"[{self.id}] {self.name}"


# ── CONTROLS AND GAPS ────────────────────────────────────────────────────────
#
# Implemented controls (status="implemented") and known gaps (status="gap")
# live in one list.  The ``.. pytm:: :controls:`` and ``.. pytm:: :gaps:``
# Sphinx directives split the list on ``status`` at render time.
#
# Associate a control with a pytm element via ``to_pytm()``:
#
#   threat = dfetch_cli        # or any pytm element
#   ctrl = CONTROLS[0]         # C-001
#   # Log the association as a traceability comment:
#   threat.controls.sanitizesInput = True  # ctrl.to_pytm() → [C-001] …

CONTROLS: list[Control] = [
    # ── Implemented controls (status="implemented") ──────────────────────────
    Control(
        id="C-001",
        name="Path-traversal prevention",
        assets=["PA-02", "SA-05"],
        description=(
            "``check_no_path_traversal()`` resolves both the candidate path and the "
            "destination root via ``os.path.realpath`` (symlink-aware, not "
            "``pathlib.Path.resolve``), then rejects any path whose resolved prefix "
            "does not start with the resolved root.  Applied to every file copy and "
            "post-extraction symlink."
        ),
        reference="dfetch/util/util.py",
    ),
    Control(
        id="C-002",
        name="Decompression-bomb protection",
        assets=["SA-05", "PA-02"],
        description=(
            "Archives are rejected if the uncompressed size exceeds 500 MB or the "
            "member count exceeds 10 000."
        ),
        reference="dfetch/vcs/archive.py",
    ),
    Control(
        id="C-003",
        name="Archive symlink validation",
        assets=["PA-02"],
        description=(
            "Absolute and escaping (``..``) symlink targets are rejected for both "
            "TAR and ZIP.  A post-extraction walk validates all symlinks against the "
            "manifest root."
        ),
        reference="dfetch/vcs/archive.py",
    ),
    Control(
        id="C-004",
        name="Archive member type checks",
        assets=["PA-02", "SA-05"],
        description=(
            "TAR and ZIP members of type device file or FIFO are rejected outright."
        ),
        reference="dfetch/vcs/archive.py",
    ),
    Control(
        id="C-005",
        name="Integrity hash verification",
        assets=["PA-02", "PA-03"],
        description=(
            "SHA-256, SHA-384, and SHA-512 verified via ``hmac.compare_digest`` "
            "(constant-time comparison, resistant to timing attacks)."
        ),
        reference="dfetch/vcs/integrity_hash.py",
    ),
    Control(
        id="C-006",
        name="Non-interactive VCS",
        assets=["SA-02", "EA-01"],
        description=(
            "``GIT_TERMINAL_PROMPT=0``, ``BatchMode=yes`` for Git; "
            "``--non-interactive`` for SVN.  Credential prompts are suppressed to "
            "prevent interactive hijacking in CI."
        ),
        reference="dfetch/vcs/git.py, dfetch/vcs/svn.py",
    ),
    Control(
        id="C-007",
        name="Subprocess safety",
        assets=["SA-01"],
        description=(
            "All external commands invoked with ``shell=False`` and list-form "
            "arguments — no shell-injection vector."
        ),
        reference="dfetch/util/cmdline.py",
    ),
    Control(
        id="C-008",
        name="Manifest input validation",
        assets=["PA-01"],
        description=(
            "StrictYAML schema with ``SAFE_STR = Regex(r\"^[^\\x00-\\x1F\\x7F-\\x9F]*$\")`` "
            "rejects control characters in all string fields."
        ),
        reference="dfetch/manifest/schema.py",
    ),
    Control(
        id="C-009",
        name="Actions commit-SHA pinning",
        assets=["SA-06", "EA-04"],
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
        description=(
            "All ``actions/checkout`` steps drop the GitHub token from the working "
            "tree after checkout."
        ),
        reference=".github/workflows/*.yml",
    ),
    Control(
        id="C-013",
        name="Harden-runner (egress audit)",
        assets=["SA-02", "EA-04"],
        description=(
            "``step-security/harden-runner`` is used in every workflow to audit "
            "outbound network connections.  Policy is ``audit``, not ``block``."
        ),
        reference=".github/workflows/*.yml",
    ),
    Control(
        id="C-014",
        name="OpenSSF Scorecard",
        assets=["EA-03", "SA-10"],
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
        description=(
            "``bandit -r dfetch`` runs in CI to detect common Python security issues."
        ),
        reference="pyproject.toml",
    ),
    # ── Gaps: unimplemented controls (status="gap") ──────────────────────────
    Control(
        id="C-018",
        name="Optional integrity hash",
        assets=["PA-02", "PA-03"],
        status="gap",
        description=(
            "``integrity.hash`` in the manifest is optional.  Archive dependencies "
            "without it have no content-authenticity guarantee.  Plain ``http://`` "
            "URLs receive no protection at all."
        ),
    ),
    Control(
        id="C-019",
        name="No integrity mechanism for Git/SVN",
        assets=["PA-02", "PA-03"],
        status="gap",
        description=(
            "Git and SVN dependencies carry no equivalent to ``integrity.hash``.  "
            "Authenticity relies entirely on transport security (TLS or SSH).  "
            "Mutable references (branch, tag) can silently fetch different content "
            "after an upstream force-push."
        ),
    ),
    Control(
        id="C-020",
        name="No patch-file integrity",
        assets=["SA-04", "PA-02"],
        status="gap",
        description=(
            "Patch files referenced in the manifest carry no integrity hash.  A "
            "tampered patch can write to arbitrary paths through ``patch-ng``."
        ),
    ),
    Control(
        id="C-021",
        name="No SLSA provenance",
        assets=["PA-04"],
        status="gap",
        description=(
            "The release pipeline does not generate SLSA provenance attestations or "
            "Sigstore/cosign signatures for the published wheel.  Consumers cannot "
            "verify build provenance."
        ),
    ),
    Control(
        id="C-022",
        name="No dfetch-self SBOM on PyPI",
        assets=["PA-04", "PA-05"],
        status="gap",
        description=(
            "The CycloneDX SBOM generated by ``dfetch report`` covers vendored "
            "dependencies only.  dfetch itself has no machine-readable SBOM published "
            "alongside its PyPI release, as CRA Article 13 requires."
        ),
    ),
    Control(
        id="C-023",
        name="Build deps without hash pinning",
        assets=["SA-09"],
        status="gap",
        description=(
            "``pip install .`` and ``pip install --upgrade pip build`` in CI do not "
            "use ``--require-hashes``.  A compromised PyPI mirror can substitute "
            "malicious build tooling."
        ),
    ),
    Control(
        id="C-024",
        name="``secrets: inherit`` scope",
        assets=["SA-06", "SA-02"],
        status="gap",
        description=(
            "``ci.yml`` passes all repository secrets to the test and docs workflows "
            "via ``secrets: inherit``.  A malicious pull request step in either "
            "workflow could exfiltrate secrets."
        ),
    ),
    Control(
        id="C-025",
        name="Harden-runner in audit mode",
        assets=["EA-04", "SA-06"],
        status="gap",
        description=(
            "``step-security/harden-runner`` is configured with "
            "``egress-policy: audit``.  Outbound connections are logged but not "
            "blocked — secret exfiltration via a compromised CI step is possible."
        ),
    ),
]

# ── ASSET → CONTROL INDEX ────────────────────────────────────────────────────
#
# Maps each asset ID to the controls (or gaps) that apply to it.
# Use to_pytm() for a human-readable label; e.g.:
#
#   for ctrl in ASSET_CONTROLS.get("PA-02", []):
#       print(ctrl.to_pytm())   # → "[C-001] Path-traversal prevention"

ASSET_CONTROLS: dict[str, list[Control]] = {}
for _ctrl in CONTROLS:
    for _asset_id in _ctrl.assets:
        ASSET_CONTROLS.setdefault(_asset_id, []).append(_ctrl)

if __name__ == "__main__":
    tm.process()
