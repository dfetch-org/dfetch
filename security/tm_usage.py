"""Runtime-usage threat model for dfetch.

Scope: post-install lifecycle — reading the manifest, fetching dependencies
from VCS and archive sources, applying patches, writing vendored files, and
generating reports (SBOM, SARIF, check output).

The installed dfetch package (produced by the supply chain modelled in
``tm_supply_chain.py``) is the entry point for this model.

Run::

    python -m security.tm_usage --dfd
    python -m security.tm_usage --seq
    python -m security.tm_usage --report
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
    make_usage_assumptions,
)

# ── Threat model metadata ────────────────────────────────────────────────────

TM.reset()

tm = TM(
    "dfetch Runtime Usage",
    description=(
        "EN 18031 / CRA runtime-usage threat model for dfetch.  "
        "Covers the post-install lifecycle: reading the manifest, fetching "
        "dependencies from VCS and archive sources, applying patches, writing "
        "vendored files, and generating reports (SBOM, SARIF, check output).  "
        "The installed dfetch package — produced by the supply chain in "
        "tm_supply_chain.py — is the entry point."
    ),
    isOrdered=True,
    mergeResponses=True,
    threatsFile=THREATS_FILE,
)

tm.assumptions = make_usage_assumptions()

# ── Trust boundaries ─────────────────────────────────────────────────────────

boundary_dev_env = make_dev_env_boundary()
boundary_network = make_network_boundary()

boundary_remote_vcs = Boundary("Remote VCS Infrastructure")
boundary_remote_vcs.description = (
    "Upstream Git and SVN servers (GitHub, GitLab, Gitea, self-hosted).  "
    "Not controlled by the dfetch project; content is untrusted until verified."
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
developer.description = (
    "Writes and reviews ``dfetch.yaml``; selects upstream sources, pins "
    "revisions, and optionally enables ``integrity.hash`` for archive "
    "dependencies.  Trusted at workstation invocation time.  "
    "Responsible for choosing trustworthy upstream sources and keeping "
    "pins current."
)

# ── External entities ────────────────────────────────────────────────────────

remote_git_svn = ExternalEntity("EA-01: Remote VCS Server")
remote_git_svn.inBoundary = boundary_remote_vcs
remote_git_svn.classification = Classification.PUBLIC
remote_git_svn.description = (
    "Upstream Git or SVN host: GitHub, GitLab, Gitea, self-hosted Git/SVN.  "
    "Not controlled by the dfetch project; content is untrusted until verified."
)

archive_server = ExternalEntity("EA-02: Archive HTTP Server")
archive_server.inBoundary = boundary_remote_vcs
archive_server.classification = Classification.PUBLIC
archive_server.description = (
    "HTTP/HTTPS server serving ``.tar.gz``, ``.tgz``, ``.tar.bz2``, ``.tar.xz``, "
    "or ``.zip`` files.  CRITICAL: ``http://`` (non-TLS) URLs are accepted without "
    "enforcement of integrity hashes — the ``integrity.hash`` field is optional."
)

consumer_build = ExternalEntity("EA-07: Consumer Build System")
consumer_build.inBoundary = boundary_dev_env
consumer_build.classification = Classification.RESTRICTED
consumer_build.description = (
    "Build system that compiles fetched source code (PA-02).  "
    "Not controlled by dfetch — it receives untrusted third-party source."
)

# ── Processes ────────────────────────────────────────────────────────────────

dfetch_cli = Process("SA-01: dfetch Process")
dfetch_cli.inBoundary = boundary_dev_env
dfetch_cli.classification = Classification.RESTRICTED
dfetch_cli.description = (
    "Python CLI entry point dispatching to: update, check, diff, add, remove, "
    "patch, format-patch, freeze, import, report, validate, environment.  "
    "Invokes Git and SVN as subprocesses (``shell=False``, list args).  "
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

# ── PRIMARY ASSETS ───────────────────────────────────────────────────────────

manifest_store = Datastore("PA-01: dfetch Manifest")
manifest_store.inBoundary = boundary_dev_env
manifest_store.description = (
    "``dfetch.yaml`` — declares all upstream sources (URL/VCS type), version pins "
    "(branch / tag / revision / SHA), dst paths, patch references, and optional "
    "integrity hashes.  "
    "Tampering redirects fetches to attacker-controlled sources.  "
    "RISK: ``integrity.hash`` is Optional in schema — archive deps can be declared "
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
    "Third-party source code written to the ``dst:`` path after extraction / "
    "checkout.  Becomes a direct build input for the consuming project.  "
    "A compromised upstream or MITM can inject malicious code that executes in "
    "the consumer's build system, test runner, or production binary."
)
fetched_source.storesSensitiveData = True
fetched_source.hasWriteAccess = True
fetched_source.isSQL = False
fetched_source.classification = Classification.SENSITIVE
fetched_source.controls.isEncryptedAtRest = False

integrity_hash_record = Datastore("PA-03: Integrity Hash Record")
integrity_hash_record.inBoundary = boundary_dev_env
integrity_hash_record.description = (
    "``integrity.hash:`` field in ``dfetch.yaml`` (sha256/sha384/sha512:<hex>).  "
    "The sole trust anchor for archive-type dependencies.  "
    "Verified via ``hmac.compare_digest`` (constant-time).  "
    "CRITICAL GAP: field is Optional — absence disables all content verification.  "
    "CRITICAL GAP: Git and SVN deps have NO equivalent integrity mechanism; "
    "authenticity relies entirely on transport security (TLS/SSH)."
)
integrity_hash_record.storesSensitiveData = False
integrity_hash_record.hasWriteAccess = True
integrity_hash_record.isSQL = False
integrity_hash_record.classification = Classification.SENSITIVE
integrity_hash_record.controls.providesIntegrity = True

sbom_output = Datastore("PA-05: SBOM Output (CycloneDX)")
sbom_output.inBoundary = boundary_dev_env
sbom_output.description = (
    "CycloneDX JSON/XML produced by ``dfetch report -t sbom``.  "
    "Enumerates vendored components with PURL, license, and hash.  "
    "Falsification hides actual dependencies from downstream CVE scanners.  "
    "NOTE: this SBOM covers vendored deps only — dfetch itself has a separate "
    "machine-readable SBOM published on PyPI (see PA-04 in tm_supply_chain.py)."
)
sbom_output.storesSensitiveData = False
sbom_output.hasWriteAccess = True
sbom_output.isSQL = False
sbom_output.classification = Classification.RESTRICTED

# ── SUPPORTING ASSETS ────────────────────────────────────────────────────────

vcs_credentials = Data(
    "SA-02: VCS Credentials",
    description=(
        "SSH private keys, HTTPS Personal Access Tokens, SVN passwords.  "
        "Used to authenticate to private upstream repositories.  "
        "dfetch never persists these — managed by OS keychain, SSH agent, "
        "or CI secret store."
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
    "``.dfetch_data.yaml`` files written after each successful fetch.  "
    "Contains: remote_url, revision/branch/tag, hash, last-fetch timestamp.  "
    "Read by ``dfetch check`` to detect outdated deps.  "
    "Tampering can suppress update notifications — an attacker who controls the "
    "local filesystem can silently mask a compromised vendored dep."
)
metadata_store.storesSensitiveData = False
metadata_store.hasWriteAccess = True
metadata_store.isSQL = False
metadata_store.classification = Classification.RESTRICTED

patch_store = Datastore("SA-04: Patch Files")
patch_store.inBoundary = boundary_dev_env
patch_store.description = (
    "Unified-diff ``.patch`` files referenced by ``patch:`` in ``dfetch.yaml``.  "
    "Applied by ``patch-ng`` after fetch.  "
    "A malicious patch can write to arbitrary destination paths — "
    "dfetch's path-traversal guards apply to archive extraction but ``patch-ng``'s "
    "own path safety depends on its internal implementation.  "
    "Patch files are not integrity-verified (no hash in manifest schema)."
)
patch_store.storesSensitiveData = False
patch_store.hasWriteAccess = True
patch_store.isSQL = False
patch_store.classification = Classification.RESTRICTED

local_vcs_cache = Datastore("SA-05: Local VCS Cache (temp)")
local_vcs_cache.inBoundary = boundary_dev_env
local_vcs_cache.description = (
    "Temporary directory used during git-clone / svn-checkout / archive extraction.  "
    "Deleted after content is copied to dst.  "
    "Path-traversal attacks targeting this space are mitigated by "
    "``check_no_path_traversal()`` and post-extraction symlink walks."
)
local_vcs_cache.storesSensitiveData = False
local_vcs_cache.hasWriteAccess = True
local_vcs_cache.isSQL = False
local_vcs_cache.classification = Classification.RESTRICTED

audit_reports = Datastore("SA-08: Audit / Check Reports")
audit_reports.inBoundary = boundary_dev_env
audit_reports.description = (
    "SARIF, Jenkins warnings-ng, Code Climate JSON produced by ``dfetch check``.  "
    "Falsification hides vulnerabilities from downstream security dashboards."
)
audit_reports.storesSensitiveData = False
audit_reports.hasWriteAccess = True
audit_reports.isSQL = False
audit_reports.classification = Classification.RESTRICTED

# ── DATA FLOWS ───────────────────────────────────────────────────────────────

df01 = Dataflow(developer, dfetch_cli, "DF-01: Invoke dfetch command")
df01.description = "CLI invocation: update / check / diff / report / add etc."

df02 = Dataflow(manifest_store, dfetch_cli, "DF-02: Read manifest")
df02.description = "StrictYAML parse; SAFE_STR regex rejects control characters."
df02.controls.validatesInput = True

df03_tls = Dataflow(dfetch_cli, remote_git_svn, "DF-03a: Fetch VCS content — HTTPS/SSH")
df03_tls.description = (
    "``git fetch`` / ``git ls-remote`` over HTTPS or SSH.  "
    "HTTPS follows up to 10 redirects.  SSH enforces ``BatchMode=yes`` and "
    "``GIT_TERMINAL_PROMPT=0`` (no credential prompts).  SVN over "
    "``svn+https://`` or SSH tunnel.  Transport is encrypted and host identity "
    "verified."
)
df03_tls.protocol = "HTTPS / SSH"
df03_tls.controls.isEncrypted = True
df03_tls.controls.isHardened = True  # BatchMode=yes, --non-interactive

df03_plain = Dataflow(
    dfetch_cli, remote_git_svn, "DF-03b: Fetch VCS content — svn:// / http://"
)
df03_plain.description = (
    "``git fetch`` over ``http://`` or SVN over ``svn://`` (plain, non-TLS).  "
    "dfetch accepts these protocols without enforcement — no TLS check in manifest "
    "schema.  Traffic is unencrypted; MITM can substitute repository content.  "
    "RECOMMENDATION: restrict manifest URLs to HTTPS / svn+https:// / SSH."
)
df03_plain.protocol = "http / svn"
df03_plain.controls.isEncrypted = False
df03_plain.controls.isHardened = False

df04_tls = Dataflow(
    remote_git_svn, dfetch_cli, "DF-04a: VCS content inbound — HTTPS/SSH"
)
df04_tls.description = (
    "Repository tree and file content over HTTPS or SSH.  Transport is encrypted.  "
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
    "Repository content over unencrypted ``http://`` or ``svn://``.  "
    "A network-positioned attacker can substitute arbitrary content without "
    "detection — no transport encryption and no content hash."
)
df04_plain.protocol = "http / svn"
df04_plain.controls.isEncrypted = False
df04_plain.controls.providesIntegrity = False

df05 = Dataflow(dfetch_cli, archive_server, "DF-05: Archive download request")
df05.description = (
    "HTTP GET to archive URL.  Follows up to 10 3xx redirects.  "
    "RISK: ``http://`` (non-TLS) URLs accepted — request and response are "
    "unencrypted."
)
df05.protocol = "HTTP or HTTPS"
df05.controls.isEncrypted = False  # not guaranteed; http:// accepted

df06 = Dataflow(archive_server, dfetch_cli, "DF-06: Archive bytes (untrusted)")
df06.description = (
    "Raw archive bytes streamed into dfetch.  "
    "Hash computed in-flight when ``integrity.hash`` is specified.  "
    "CRITICAL: when ``integrity.hash`` is absent, no content verification occurs."
)
df06.protocol = "HTTP or HTTPS"
df06.controls.providesIntegrity = False  # hash is optional; may be absent
df06.controls.isEncrypted = False  # http:// allowed

df07 = Dataflow(dfetch_cli, fetched_source, "DF-07: Write vendored files")
df07.description = (
    "Post-validation copy to dst path.  Path-traversal checked via "
    "``check_no_path_traversal()``.  Symlinks validated post-extraction."
)
df07.controls.sanitizesInput = True
df07.controls.providesIntegrity = False  # conditional on hash presence in DF-05/06

df08 = Dataflow(dfetch_cli, metadata_store, "DF-08: Write dependency metadata")
df08.description = "Writes ``.dfetch_data.yaml`` tracking remote_url, revision, hash."

df09 = Dataflow(dfetch_cli, sbom_output, "DF-09: Write SBOM")
df09.description = "CycloneDX BOM generation from metadata store contents."

df10 = Dataflow(patch_store, dfetch_cli, "DF-10: Read and apply patch")
df10.description = (
    "``patch-ng`` reads unified-diff file and applies to vendor directory.  "
    "RISK: patch files are not integrity-verified (no hash in manifest schema).  "
    "``patch-ng`` path safety depends on its own internal implementation."
)
df10.controls.validatesInput = False  # no integrity hash on patch files

df15 = Dataflow(fetched_source, consumer_build, "DF-15: Vendored source to build")
df15.description = (
    "Fetched and patched source code consumed by the project build system.  "
    "The build system receives third-party source whose integrity depends on "
    "the controls applied during DF-05 through DF-10."
)

# ── CONTROLS AND GAPS ────────────────────────────────────────────────────────

CONTROLS: list[Control] = [
    # ── Implemented controls ─────────────────────────────────────────────────
    Control(
        id="C-001",
        name="Path-traversal prevention",
        assets=["PA-02", "SA-05"],
        threats=["DFT-03"],
        description=(
            "``check_no_path_traversal()`` resolves both the candidate path and the "
            "destination root via ``os.path.realpath`` (symlink-aware), then rejects "
            "any path whose resolved prefix does not start with the resolved root.  "
            "Applied to every file copy and post-extraction symlink."
        ),
        reference="dfetch/util/util.py",
    ),
    Control(
        id="C-002",
        name="Decompression-bomb protection",
        assets=["SA-05", "PA-02"],
        threats=["DFT-09"],
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
        threats=["DFT-03"],
        description=(
            "Absolute and escaping (``..``) symlink targets are rejected for both "
            "TAR and ZIP.  A post-extraction walk validates all symlinks against "
            "the manifest root."
        ),
        reference="dfetch/vcs/archive.py",
    ),
    Control(
        id="C-004",
        name="Archive member type checks",
        assets=["PA-02", "SA-05"],
        threats=["DFT-03"],
        description=(
            "TAR and ZIP members of type device file or FIFO are rejected outright."
        ),
        reference="dfetch/vcs/archive.py",
    ),
    Control(
        id="C-005",
        name="Integrity hash verification",
        assets=["PA-02", "PA-03"],
        threats=["DFT-01", "DFT-02", "DFT-05"],
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
        threats=["DFT-06"],
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
        threats=["DFT-06"],
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
        threats=["DFT-04", "DFT-08"],
        description=(
            r'StrictYAML schema with ``SAFE_STR = Regex(r"^[^\x00-\x1F\x7F-\x9F]*$")`` '
            "rejects control characters in all string fields."
        ),
        reference="dfetch/manifest/schema.py",
    ),
    # ── Gaps ─────────────────────────────────────────────────────────────────
    Control(
        id="C-018",
        name="Optional integrity hash",
        assets=["PA-02", "PA-03"],
        threats=["DFT-01", "DFT-02"],
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
        threats=["DFT-02", "DFT-05"],
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
        threats=["DFT-08"],
        status="gap",
        description=(
            "Patch files referenced in the manifest carry no integrity hash.  A "
            "tampered patch can write to arbitrary paths through ``patch-ng``."
        ),
    ),
]

ASSET_CONTROLS: dict[str, list[Control]] = build_asset_controls_index(CONTROLS)

if __name__ == "__main__":
    tm.process()
