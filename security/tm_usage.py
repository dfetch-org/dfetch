# pylint: disable=too-many-lines
"""Runtime-usage threat model for dfetch.

Scope: post-install lifecycle - reading the manifest, fetching dependencies
from VCS and archive sources, applying patches, writing vendored files, and
generating reports (SBOM, SARIF, check output).

The installed dfetch package (produced by the supply chain modelled in
``tm_supply_chain.py``) is the entry point for this model.

Note on consumer security: This model covers dfetch's threat surface as a tool.
It does not cover threats that arise from consuming the published artifact
(PyPI wheel, installers) after vendoring is complete. Consumer-side threats
such as package installation from a compromised PyPI account, namespace
confusion, or MITM on downstream consumers are addressed in supply_chain.py.
Consumers of dfetch-vendored dependencies inherit the integrity and trust
properties established by dfetch's controls — a compromised vendored library
will execute in the consumer's build with the same privileges as dfetch grants.

Run::

    python -m security.tm_usage --dfd
    python -m security.tm_usage --seq
    python -m security.tm_usage --report REPORT
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
    make_network_boundary,
    make_usage_assumptions,
    run_model,
)


def _make_usage_boundaries() -> tuple[Boundary, Boundary]:
    """Create and return usage model trust boundaries."""
    b_dev = make_dev_env_boundary()
    make_network_boundary()  # auto-registers; not directly referenced by any element
    b_remote_vcs = Boundary("Remote VCS Infrastructure")
    b_remote_vcs.description = (
        "Upstream Git and SVN servers (GitHub, GitLab, Gitea, self-hosted).  "
        "Not controlled by the dfetch project; content is untrusted until verified."
    )
    return b_dev, b_remote_vcs


def _make_usage_actors_and_external_entities(
    b_dev: Boundary,
    b_remote_vcs: Boundary,
) -> tuple[Actor, ExternalEntity, ExternalEntity, ExternalEntity, Datastore]:
    """Create actors and external entities; return all for use in dataflows."""
    developer = Actor("Developer")
    developer.inBoundary = b_dev
    developer.description = (
        "Writes and reviews ``dfetch.yaml``; selects upstream sources, pins "
        "revisions, and optionally enables ``integrity.hash`` for archive "
        "dependencies.  Trusted at workstation invocation time.  "
        "Responsible for choosing trustworthy upstream sources and keeping "
        "pins current."
    )
    remote_git_svn = ExternalEntity("A-09: Remote VCS Server")
    remote_git_svn.inBoundary = b_remote_vcs
    remote_git_svn.classification = Classification.PUBLIC
    remote_git_svn.description = (
        "Upstream Git or SVN host: GitHub, GitLab, Gitea, self-hosted Git/SVN.  "
        "Not controlled by the dfetch project; content is untrusted until verified.  "
        "The SLSA source level of any upstream is unknown and unverified - dfetch does "
        "not check whether the upstream enforces branch protection, mandatory review, or "
        "ancestry enforcement, and no VSA is fetched alongside repository content (A-23).  "
        "Threat postures: a compromised upstream maintainer account (phishing, credential "
        "stuffing, or MFA bypass) delivers attacker-controlled commits over an authenticated "
        "channel where transport security gives no protection — mitigated only by commit-SHA "
        "pinning and review before accepting any update.  "
        "A network-adjacent attacker (BGP hijack, compromised DNS resolver) can intercept "
        "unencrypted traffic (svn://, http://) and inject redirects, but cannot break "
        "correctly implemented TLS or SSH."
    )
    archive_server = ExternalEntity("A-10: Archive HTTP Server")
    archive_server.inBoundary = b_remote_vcs
    archive_server.classification = Classification.PUBLIC
    archive_server.description = (
        "HTTP/HTTPS server serving ``.tar.gz``, ``.tgz``, ``.tar.bz2``, ``.tar.xz``, "
        "or ``.zip`` files.  CRITICAL: ``http://`` (non-TLS) URLs are accepted without "
        "enforcement of integrity hashes - the ``integrity.hash`` field is optional.  "
        "Threat postures: a network-adjacent attacker (BGP hijack, compromised DNS resolver, "
        "or corporate proxy) can intercept ``http://`` traffic and serve a malicious archive "
        "transparently — ``integrity.hash`` is the only defence for plain-HTTP URLs.  "
        "A compromised CDN node or registry can serve malicious content under a valid TLS "
        "certificate; transport integrity gives no protection — only a verified content hash "
        "or signed attestation detects server-side substitution."
    )
    upstream_source_attestation = Datastore("A-23: Upstream Source Attestation (VSA)")
    upstream_source_attestation.inBoundary = b_remote_vcs
    upstream_source_attestation.classification = Classification.PUBLIC
    upstream_source_attestation.description = (
        "SLSA Source Provenance Attestation or Verification Summary Attestation (VSA) "
        "that an upstream VCS host can publish for a specific revision, attesting that "
        "the source-level controls required by a given SLSA source level - branch "
        "protection, mandatory review, and ancestry enforcement - were applied.  "
        "CRITICAL: dfetch has no mechanism to request or verify source-level attestations "
        "and the manifest schema has no field to declare an expected SLSA source level.  "
        "In the absence of a VSA the consumer cannot cryptographically distinguish a "
        "well-governed upstream from one with no controls at all."
    )
    upstream_source_attestation.storesSensitiveData = False
    upstream_source_attestation.hasWriteAccess = False
    upstream_source_attestation.isSQL = False
    upstream_source_attestation.controls.usesCodeSigning = (
        False  # no VSA published by upstream
    )
    upstream_source_attestation.controls.providesIntegrity = (
        False  # no verification possible
    )
    consumer_build = ExternalEntity("A-11: Consumer Build System")
    consumer_build.inBoundary = b_dev
    consumer_build.classification = Classification.RESTRICTED
    consumer_build.description = (
        "Build system that compiles fetched source code (A-13).  "
        "Not controlled by dfetch - it receives untrusted third-party source."
    )
    return (
        developer,
        remote_git_svn,
        archive_server,
        consumer_build,
        upstream_source_attestation,
    )


def _make_usage_processes(b_dev: Boundary) -> tuple[Process, Process]:
    """Create dfetch process elements; return those referenced by dataflows."""
    dfetch_cli = Process("A-22: dfetch Process")
    dfetch_cli.inBoundary = b_dev
    dfetch_cli.classification = Classification.RESTRICTED
    dfetch_cli.description = (
        "Python CLI entry point dispatching to: update, check, diff, add, remove, "
        "update-patch, format-patch, freeze, import, init, report, validate, environment.  "
        "Invokes Git and SVN as subprocesses (``shell=False``, list args).  "
        "Extracts archives with decompression-bomb limits and path-traversal checks."
    )
    dfetch_cli.controls.validatesInput = True  # StrictYAML + SAFE_STR regex
    dfetch_cli.controls.sanitizesInput = True  # check_no_path_traversal realpath-based
    dfetch_cli.controls.usesParameterizedInput = (
        True  # shell=False, list-based subprocesses
    )
    dfetch_cli.controls.checksInputBounds = True  # 500MB / 10k-member archive limits
    dfetch_cli.controls.isHardened = (
        True  # BatchMode=yes, --non-interactive, type checks
    )
    dfetch_cli.controls.providesIntegrity = True  # hmac.compare_digest SHA-256/384/512
    dfetch_cli.controls.hashVerification = (
        True  # sha256/sha384/sha512 allowlist enforced
    )
    dfetch_cli.controls.invokesSubprocess = (
        True  # git/svn invoked as list-arg subprocesses
    )
    patch_apply = Process("Patch Application (patch-ng)")
    patch_apply.inBoundary = b_dev
    patch_apply.description = (
        "Invokes ``patch-ng`` to apply unified-diff files from ``patch:`` references "
        "in the manifest.  Path safety is delegated entirely to ``patch-ng``'s internal "
        "implementation - dfetch does not independently sanitise patch-file destination "
        "paths before handing off to the library."
    )
    patch_apply.controls.sanitizesInput = (
        False  # path safety delegated to patch-ng; not independently verified
    )
    patch_apply.controls.validatesInput = (
        False  # no integrity hash on patch files (gap C-020)
    )
    patch_apply.controls.usesParameterizedInput = True  # Python library call, no shell
    return dfetch_cli, patch_apply


def _make_usage_datastores_a(
    b_dev: Boundary,
) -> tuple[Datastore, Datastore, Datastore, Datastore]:
    """Create primary data stores; return all for use in dataflows."""
    manifest_store = Datastore("A-12: dfetch Manifest")
    manifest_store.inBoundary = b_dev
    manifest_store.description = (
        "``dfetch.yaml`` - declares all upstream sources (URL/VCS type), version pins "
        "(branch / tag / revision / SHA), dst paths, patch references, and optional "
        "integrity hashes.  "
        "Tampering redirects fetches to attacker-controlled sources.  "
        "RISK: ``integrity.hash`` is Optional in schema - archive deps can be declared "
        "without any content-authenticity guarantee.  "
        "Threat postures: a malicious manifest contributor introduces a ``dfetch.yaml`` "
        "change that redirects a dep to an attacker-controlled URL, points ``dst:`` at a "
        "sensitive path, or embeds a credential-bearing URL — dfetch is not the control "
        "point; code review at the PR boundary is the intended mitigating control.  "
        "A local-filesystem attacker with write access to the working tree (gained via a "
        "compromised dev dependency, malicious post-install hook, or lateral movement) can "
        "tamper with ``.dfetch_data.yaml``, patch files, and vendored source after dfetch "
        "writes them to disk."
    )
    manifest_store.storesSensitiveData = (
        False  # config only (URLs, pins, hashes), not credentials/PII
    )
    manifest_store.hasWriteAccess = True
    manifest_store.isSQL = False
    manifest_store.classification = Classification.SENSITIVE
    manifest_store.controls.isEncryptedAtRest = False
    manifest_store.controls.validatesInput = True  # StrictYAML validation on read
    manifest_store.controls.providesIntegrity = (
        True  # integrity.hash field is the content-authenticity mechanism
    )
    fetched_source = Datastore("A-13: Fetched Source Code")
    fetched_source.inBoundary = b_dev
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
    integrity_hash_record = Datastore("A-14: Integrity Hash Record")
    integrity_hash_record.inBoundary = b_dev
    integrity_hash_record.description = (
        "``integrity.hash:`` field in ``dfetch.yaml`` (sha256/sha384/sha512:<hex>).  "
        "Primary trust anchor for archive-type dependencies when present.  "
        "Verified via ``hmac.compare_digest`` (constant-time).  "
        "Field is optional - absence disables content verification for archives (C-018).  "
        "Git and SVN have no equivalent; they rely entirely on transport security (C-019)."
    )
    integrity_hash_record.storesSensitiveData = False
    integrity_hash_record.hasWriteAccess = True
    integrity_hash_record.isSQL = False
    integrity_hash_record.classification = Classification.SENSITIVE
    integrity_hash_record.controls.providesIntegrity = True
    sbom_output = Datastore("A-15: SBOM Output (CycloneDX)")
    sbom_output.inBoundary = b_dev
    sbom_output.description = (
        "CycloneDX JSON/XML produced by ``dfetch report -t sbom``.  "
        "Enumerates vendored components with PURL, license, and hash.  "
        "Falsification hides actual dependencies from downstream CVE scanners.  "
        "NOTE: this SBOM covers vendored deps only - dfetch itself has a separate "
        "machine-readable SBOM published on PyPI (see A-04 in tm_supply_chain.py)."
    )
    sbom_output.storesSensitiveData = False
    sbom_output.hasWriteAccess = True
    sbom_output.isSQL = False
    sbom_output.classification = Classification.RESTRICTED
    return manifest_store, fetched_source, sbom_output, integrity_hash_record


def _make_usage_datastores_b(b_dev: Boundary) -> tuple[Data, Datastore, Datastore]:
    """Create credential and audit data stores; return those referenced by dataflows."""
    Data(
        "A-16: VCS Credentials",
        description=(
            "SSH private keys, HTTPS Personal Access Tokens, SVN passwords.  "
            "Used to authenticate to private upstream repositories.  "
            "dfetch never persists these - managed by OS keychain, SSH agent, "
            "or CI secret store."
        ),
        classification=Classification.SECRET,
        isCredentials=True,
        isPII=False,
        isStored=False,
        isDestEncryptedAtRest=False,
        isSourceEncryptedAtRest=True,
    )
    embedded_url_credential = Data(
        "A-17: Embedded Credential in Remote URL",
        description=(
            "A VCS or archive URL that encodes a credential in the userinfo component "
            "(e.g. ``https://user:TOKEN@github.com/org/repo.git``).  "
            "dfetch writes ``remote_url`` verbatim to ``.dfetch_data.yaml`` after each "
            "successful fetch.  If the URL contains a Personal Access Token or password, "
            "that credential is persisted in plaintext and typically committed to VCS, "
            "where it becomes readable from every clone and CI checkout indefinitely."
        ),
        classification=Classification.SECRET,
        isCredentials=True,
        isPII=False,
        isStored=True,  # written verbatim to .dfetch_data.yaml
        isDestEncryptedAtRest=False,  # .dfetch_data.yaml is plaintext on disk
        isSourceEncryptedAtRest=False,
    )
    metadata_store = Datastore("A-18: Dependency Metadata")
    metadata_store.inBoundary = b_dev
    metadata_store.description = (
        "``.dfetch_data.yaml`` files written after each successful fetch.  "
        "Contains: remote_url, revision/branch/tag, hash, last-fetch timestamp.  "
        "Read by ``dfetch check`` to detect outdated deps.  "
        "Tampering can suppress update notifications - an attacker who controls the "
        "local filesystem can silently mask a compromised vendored dep."
    )
    metadata_store.storesSensitiveData = False
    metadata_store.hasWriteAccess = True
    metadata_store.isSQL = False
    metadata_store.classification = Classification.RESTRICTED
    metadata_store.isCredentials = True  # may contain credential-bearing URLs verbatim
    metadata_store.isStored = True
    metadata_store.isDestEncryptedAtRest = False  # plaintext on disk
    patch_store = Datastore("A-19: Patch Files")
    patch_store.inBoundary = b_dev
    patch_store.description = (
        "Unified-diff ``.patch`` files referenced by ``patch:`` in ``dfetch.yaml``.  "
        "Applied by ``patch-ng`` after fetch.  "
        "A malicious patch can write to arbitrary destination paths - "
        "dfetch's path-traversal guards apply to archive extraction but ``patch-ng``'s "
        "own path safety depends on its internal implementation.  "
        "Patch files are not integrity-verified (no hash in manifest schema)."
    )
    patch_store.storesSensitiveData = False
    patch_store.hasWriteAccess = True
    patch_store.isSQL = False
    patch_store.classification = Classification.RESTRICTED
    return embedded_url_credential, metadata_store, patch_store


def _make_usage_vcs_dataflows(
    developer: Actor,
    dfetch_cli: Process,
    manifest_store: Datastore,
    remote_git_svn: ExternalEntity,
) -> None:
    """Create VCS-related dataflows; all auto-register with TM."""
    df01 = Dataflow(developer, dfetch_cli, "DF-01: Invoke dfetch command")
    df01.description = "CLI invocation: update / check / diff / report / add etc."
    df02 = Dataflow(manifest_store, dfetch_cli, "DF-02: Read manifest")
    df02.description = "StrictYAML parse; SAFE_STR regex rejects control characters."
    df02.controls.validatesInput = True
    df03_tls = Dataflow(
        dfetch_cli, remote_git_svn, "DF-03a: Fetch VCS content - HTTPS/SSH"
    )
    df03_tls.description = (
        "``git fetch`` / ``git ls-remote`` over HTTPS or SSH.  "
        "HTTPS follows up to 10 redirects.  SSH enforces ``BatchMode=yes`` and "
        "``GIT_TERMINAL_PROMPT=0`` (no credential prompts).  SVN over "
        "``svn+https://`` or SSH tunnel.  Transport is encrypted and server "
        "identity verified against the OS trust store.  "
        "Note: transport security is not content integrity - a compromised "
        "upstream can serve attacker-controlled commits over a valid TLS "
        "channel (see gap C-019)."
    )
    df03_tls.protocol = "HTTPS / SSH"
    df03_tls.controls.isEncrypted = True
    df03_tls.controls.isHardened = True  # BatchMode=yes, --non-interactive
    df03_tls.controls.providesIntegrity = (
        True  # outbound request; integrity risk is on the response (DF-04a)
    )
    df03_tls.controls.isNetworkFlow = True
    df03_plain = Dataflow(
        dfetch_cli, remote_git_svn, "DF-03b: Fetch VCS content - svn:// / http://"
    )
    df03_plain.description = (
        "``git fetch`` over ``http://`` or SVN over ``svn://`` (plain, non-TLS).  "
        "dfetch accepts these protocols without enforcement - no TLS check in manifest "
        "schema.  Traffic is unencrypted; MITM can substitute repository content.  "
        "RECOMMENDATION: restrict manifest URLs to HTTPS / svn+https:// / SSH."
    )
    df03_plain.protocol = "http / svn"
    df03_plain.controls.isEncrypted = False
    df03_plain.controls.isHardened = False
    df03_plain.controls.isNetworkFlow = True
    df03_plain.controls.isPlaintext = True
    df04_tls = Dataflow(
        remote_git_svn, dfetch_cli, "DF-04a: VCS content inbound - HTTPS/SSH"
    )
    df04_tls.description = (
        "Repository tree and file content over HTTPS or SSH.  Transport is encrypted.  "
        "No end-to-end content hash for Git or SVN - authenticity relies on transport "
        "security and upstream repository integrity.  "
        "No SLSA Source Provenance Attestation or VSA is fetched alongside content (A-23): "
        "dfetch has no mechanism to verify the source-level controls applied by the "
        "upstream, nor whether the pinned SHA remains reachable after an ancestry rewrite."
    )
    df04_tls.protocol = "HTTPS / SSH"
    df04_tls.controls.isEncrypted = True
    df04_tls.controls.providesIntegrity = (
        False  # no end-to-end hash for git/svn content
    )
    df04_tls.controls.hasAccessControl = (
        True  # authenticated connection (HTTPS credentials / SSH key)
    )
    df04_tls.controls.isNetworkFlow = True
    df04_plain = Dataflow(
        remote_git_svn, dfetch_cli, "DF-04b: VCS content inbound - svn:// / http://"
    )
    df04_plain.description = (
        "Repository content over unencrypted ``http://`` or ``svn://``.  "
        "A network-positioned attacker can substitute arbitrary content without "
        "detection - no transport encryption and no content hash."
    )
    df04_plain.protocol = "http / svn"
    df04_plain.controls.isEncrypted = False
    df04_plain.controls.providesIntegrity = False
    df04_plain.controls.isNetworkFlow = True
    df04_plain.controls.isPlaintext = True


def _make_usage_archive_dataflows(
    dfetch_cli: Process,
    archive_server: ExternalEntity,
) -> None:
    """Create archive download dataflows; all auto-register with TM."""
    df05_tls = Dataflow(
        dfetch_cli, archive_server, "DF-05a: Archive download request - HTTPS"
    )
    df05_tls.description = (
        "HTTPS GET to archive URL.  Follows up to 10 3xx redirects.  "
        "TLS authenticates the server and encrypts the channel but does not "
        "verify the content served is what the upstream intended to publish - "
        "content integrity requires ``integrity.hash`` in the manifest (DF-06a)."
    )
    df05_tls.protocol = "HTTPS"
    df05_tls.controls.isEncrypted = True
    df05_tls.controls.providesIntegrity = (
        False  # TLS provides transport security, not content integrity
    )
    df05_tls.controls.followsRedirects = True  # follows up to 10 3xx redirects
    df05_tls.controls.isNetworkFlow = True
    df05_plain = Dataflow(
        dfetch_cli, archive_server, "DF-05b: Archive download request - HTTP"
    )
    df05_plain.description = (
        "HTTP GET to archive URL.  Follows up to 10 3xx redirects.  "
        "RISK: ``http://`` (non-TLS) URLs accepted - request and response are "
        "unencrypted."
    )
    df05_plain.protocol = "HTTP"
    df05_plain.controls.isEncrypted = False
    df05_plain.controls.followsRedirects = True  # follows up to 10 3xx redirects
    df05_plain.controls.isNetworkFlow = True
    df05_plain.controls.isPlaintext = True
    df06_tls = Dataflow(archive_server, dfetch_cli, "DF-06a: Archive bytes - HTTPS")
    df06_tls.description = (
        "Raw archive bytes streamed into dfetch over HTTPS.  "
        "Hash computed in-flight when ``integrity.hash`` is specified.  "
        "CRITICAL: when ``integrity.hash`` is absent, no content verification occurs."
    )
    df06_tls.protocol = "HTTPS"
    df06_tls.controls.isEncrypted = True
    df06_tls.controls.providesIntegrity = False  # hash is optional; may be absent
    df06_tls.controls.isNetworkFlow = True
    df06_plain = Dataflow(
        archive_server, dfetch_cli, "DF-06b: Archive bytes - HTTP (plaintext risk)"
    )
    df06_plain.description = (
        "Raw archive bytes streamed into dfetch over unencrypted HTTP.  "
        "Hash computed in-flight when ``integrity.hash`` is specified.  "
        "CRITICAL: when ``integrity.hash`` is absent, no content verification occurs.  "
        "Plaintext transport enables MITM content substitution without detection."
    )
    df06_plain.protocol = "HTTP"
    df06_plain.controls.isEncrypted = False
    df06_plain.controls.providesIntegrity = (
        False  # http:// allowed; no transport integrity
    )
    df06_plain.controls.isNetworkFlow = True
    df06_plain.controls.isPlaintext = True


def _make_usage_output_flows(
    dfetch_cli: Process,
    fetched_source: Datastore,
    metadata_store: Datastore,
    sbom_output: Datastore,
    embedded_url_credential: Data,
) -> None:
    """Create dfetch write and read-back dataflows; all auto-register with TM."""
    df07 = Dataflow(dfetch_cli, fetched_source, "DF-07: Write vendored files")
    df07.description = (
        "Post-validation copy to dst path.  Path-traversal checked via "
        "``check_no_path_traversal()``.  Symlinks validated post-extraction."
    )
    df07.controls.sanitizesInput = True
    df07.controls.isHardened = (
        True  # path-traversal and symlink checks applied before write
    )
    df07.controls.providesIntegrity = False  # conditional on hash presence in DF-05/06
    df08 = Dataflow(dfetch_cli, metadata_store, "DF-08: Write dependency metadata")
    df08.description = (
        "Writes ``.dfetch_data.yaml`` tracking remote_url, revision, hash.  "
        "A-17: if the manifest URL contains a credential in the userinfo component "
        "(e.g. ``https://user:TOKEN@host/``), it is written verbatim to this file."
    )
    df08.data = [embedded_url_credential]  # A-17: surfaces DFT-13 on this dataflow
    df09 = Dataflow(dfetch_cli, sbom_output, "DF-09: Write SBOM")
    df09.description = "CycloneDX BOM generation from metadata store contents."
    df16 = Dataflow(metadata_store, dfetch_cli, "DF-16: Read dependency metadata")
    df16.description = (
        "``dfetch check`` reads ``.dfetch_data.yaml`` to compare recorded revision and "
        "hash against upstream state.  "
        "An attacker with local filesystem write access can tamper with this file to "
        "suppress update notifications - recording a known-good hash for a compromised "
        "vendored dependency."
    )
    df16.controls.validatesInput = (
        False  # metadata is trusted as written; no integrity check on read
    )


def _make_usage_patch_and_build_flows(
    patch_apply: Process,
    patch_store: Datastore,
    fetched_source: Datastore,
    consumer_build: ExternalEntity,
) -> None:
    """Create patch application and build-handoff dataflows; all auto-register with TM."""
    df10 = Dataflow(patch_store, patch_apply, "DF-10: Read patch for application")
    df10.description = (
        "patch-ng reads the unified-diff file referenced by ``patch:`` in the manifest.  "
        "Patch files carry no integrity hash - a tampered patch is indistinguishable "
        "from a legitimate one at this stage."
    )
    df10.controls.validatesInput = False  # no integrity hash on patch files (gap C-020)
    df10b = Dataflow(
        patch_apply, fetched_source, "DF-10b: Write patched files to vendor directory"
    )
    df10b.description = (
        "patch-ng writes patched content to the vendor directory.  "
        "Path-traversal safety relies on patch-ng's own implementation; dfetch does not "
        "apply an independent ``check_no_path_traversal()`` pass on patch destinations."
    )
    df15 = Dataflow(fetched_source, consumer_build, "DF-15: Vendored source to build")
    df15.description = (
        "Fetched and patched source code consumed by the project build system.  "
        "The build system receives third-party source whose integrity depends on "
        "the controls applied during DF-05 through DF-10."
    )


def _make_usage_extraction_elements_and_flows(
    b_dev: Boundary, dfetch_cli: Process
) -> None:
    """Create archive/SVN extraction elements, their dataflows, and the cache-copy flow."""
    b_archive = Boundary("Archive Content Space")
    b_archive.description = (
        "Downloaded archive bytes before extraction and validation.  "
        "Decompression-bomb and path-traversal checks enforce this boundary during extraction."
    )
    archive_extract = Process("Archive Extraction (tarfile / zipfile)")
    archive_extract.inBoundary = b_archive
    archive_extract.description = (
        "Decompresses and extracts TAR (.tar.gz/.tgz/.tar.bz2/.tar.xz) and ZIP archives "
        "to a temporary directory.  Pre-extraction checks validate decompression-bomb "
        "limits, path traversal, symlinks, hardlinks, device files, and FIFOs.  "
        "On Python ≥ 3.11.4: ``filter='tar'`` strips setuid/setgid bits during extraction.  "
        "On Python < 3.11.4: ``extractall()`` is called without a filter - setuid, setgid, "
        "and sticky bits from TAR member headers are preserved on the extracted files, "
        "allowing a malicious archive to introduce setuid-root binaries into the vendor "
        "directory."
    )
    archive_extract.controls.checksInputBounds = True  # 500 MB / 10k member limits
    archive_extract.controls.sanitizesInput = (
        True  # path-traversal, symlink, hardlink checks
    )
    archive_extract.controls.isHardened = (
        False  # setuid/mode stripping absent on Python < 3.11.4
    )
    archive_extract.controls.isArchiveExtractor = True
    archive_extract.controls.usesParameterizedInput = (
        True  # Python library call, no shell
    )
    svn_export_proc = Process("SVN Export (svn export)")
    svn_export_proc.inBoundary = b_dev
    svn_export_proc.description = (
        "Runs ``svn export --non-interactive --force`` to check out SVN dependencies.  "
        "The ``--ignore-externals`` flag is NOT passed.  SVN repositories with "
        "``svn:externals`` properties will trigger additional fetches from third-party "
        "SVN servers not declared in ``dfetch.yaml``.  These undeclared fetches bypass "
        "dfetch's manifest controls: no integrity hash, no metadata record, and no code "
        "review of the external URL."
    )
    svn_export_proc.controls.usesParameterizedInput = (
        True  # shell=False, list-form args
    )
    svn_export_proc.controls.providesIntegrity = (
        False  # svn:externals outside manifest scope
    )
    svn_export_proc.controls.isHardened = False  # no --ignore-externals flag
    svn_export_proc.controls.invokesSubprocess = True  # svn invoked as a subprocess
    local_vcs_cache = Datastore("A-20: Local VCS Cache (temp)")
    local_vcs_cache.inBoundary = b_dev
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
    audit_reports = Datastore("A-21: Audit / Check Reports")
    audit_reports.inBoundary = b_dev
    audit_reports.description = (
        "SARIF, Jenkins warnings-ng, Code Climate JSON produced by ``dfetch check``.  "
        "Falsification hides vulnerabilities from downstream security dashboards."
    )
    audit_reports.storesSensitiveData = False
    audit_reports.hasWriteAccess = True
    audit_reports.isSQL = False
    audit_reports.classification = Classification.RESTRICTED
    df11 = Dataflow(
        dfetch_cli, archive_extract, "DF-11: Dispatch archive bytes to extraction"
    )
    df11.description = (
        "dfetch passes downloaded archive bytes to extraction; "
        "decompression-bomb and pre-extraction checks applied."
    )
    df11.controls.checksInputBounds = True
    df12 = Dataflow(
        archive_extract, local_vcs_cache, "DF-12: Write extracted archive to temp dir"
    )
    df12.description = (
        "Extracted members written to temp directory; "
        "path-traversal and symlink checks applied before each write."
    )
    df12.controls.sanitizesInput = True
    df13 = Dataflow(
        dfetch_cli, svn_export_proc, "DF-13: Dispatch SVN export subprocess"
    )
    df13.description = (
        "dfetch invokes svn export as a list-arg subprocess; "
        "svn:externals can trigger undeclared fetches outside manifest control."
    )
    df13.controls.usesParameterizedInput = True
    df13.controls.isHardened = False
    df14 = Dataflow(
        svn_export_proc, local_vcs_cache, "DF-14: Write SVN export to temp dir"
    )
    df14.description = (
        "svn export writes checked-out content to a temporary directory "
        "before dfetch copies it to the vendor dst path."
    )
    df17 = Dataflow(dfetch_cli, audit_reports, "DF-17: Write audit / check reports")
    df17.description = (
        "dfetch check writes SARIF, Jenkins warnings-ng, or Code Climate JSON; "
        "falsification hides vulnerabilities from downstream dashboards."
    )
    df22 = Dataflow(
        local_vcs_cache, dfetch_cli, "DF-22: Copy extracted content to vendor directory"
    )
    df22.description = (
        "dfetch reads the validated content from the temporary directory (A-20) and "
        "copies it to the ``dst:`` path declared in the manifest.  "
        "``check_no_path_traversal()`` is applied before each file write (C-001); "
        "symlinks are validated post-extraction."
    )
    df22.controls.sanitizesInput = True
    df22.controls.isHardened = True


def _make_usage_integrity_flows(
    dfetch_cli: Process,
    manifest_store: Datastore,
    integrity_hash_record: Datastore,
    developer: Actor,
) -> None:
    """Wire integrity-hash read/write and manifest-authorship flows."""
    df18 = Dataflow(
        integrity_hash_record,
        dfetch_cli,
        "DF-18: Read integrity hash for archive verification",
    )
    df18.description = (
        "dfetch reads the ``integrity.hash`` field (A-14) from the manifest when "
        "verifying a downloaded archive.  The hash is compared with the content "
        "digest via ``hmac.compare_digest`` (constant-time).  "
        "When the field is absent no verification occurs (gap C-018)."
    )
    df18.controls.providesIntegrity = True
    df18.controls.validatesInput = True

    df18b = Dataflow(
        dfetch_cli,
        integrity_hash_record,
        "DF-18b: Write computed hash to manifest (dfetch freeze)",
    )
    df18b.description = (
        "``dfetch freeze`` computes the SHA-256/384/512 digest of a downloaded archive "
        "and writes the ``integrity.hash`` value back into ``dfetch.yaml`` (A-14).  "
        "This is the recommended mechanism for bootstrapping a hash-pinned manifest "
        "entry; without it the field remains absent and no content verification occurs."
    )
    df18b.controls.providesIntegrity = True

    df20 = Dataflow(developer, manifest_store, "DF-20: Author / maintain dfetch.yaml")
    df20.description = (
        "Developer writes and updates ``dfetch.yaml`` (A-12): selecting upstream "
        "sources, pinning revisions, setting ``dst:`` paths, adding ``integrity.hash`` "
        "fields, and listing patch references.  "
        "The manifest is subject to code review; a malicious change can redirect "
        "any dependency fetch to an attacker-controlled URL (assumption: Manifest under "
        "code review)."
    )
    df20.controls.hasAccessControl = True


def _make_usage_gap_doc_flows(
    developer: Actor,
    patch_store: Datastore,
    remote_git_svn: ExternalEntity,
    upstream_source_attestation: Datastore,
) -> None:
    """Wire patch-file authorship and VSA gap-documentation flows."""
    df19 = Dataflow(
        remote_git_svn,
        upstream_source_attestation,
        "DF-19: VCS server publishes source attestation (not consumed by dfetch)",
    )
    df19.description = (
        "An upstream VCS host with SLSA Source Level support may publish a "
        "Source Provenance Attestation or Verification Summary Attestation (VSA) "
        "alongside repository content.  "
        "CRITICAL: dfetch has no mechanism to request or verify these attestations "
        "(gap C-035).  The flow is modelled to document the gap — dfetch does not "
        "fetch or validate A-23 at any point in its current implementation."
    )
    df19.controls.providesIntegrity = False

    df21 = Dataflow(developer, patch_store, "DF-21: Create / maintain patch files")
    df21.description = (
        "Developer authors unified-diff ``.patch`` files referenced by ``patch:`` "
        "entries in the manifest (A-19).  "
        "Patch files carry no integrity hash and are applied directly by patch-ng; "
        "a tampered or attacker-supplied patch can write to arbitrary paths (gap C-020)."
    )


def _make_usage_stores_and_flows(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    b_dev: Boundary,
    developer: Actor,
    remote_git_svn: ExternalEntity,
    archive_server: ExternalEntity,
    consumer_build: ExternalEntity,
    upstream_source_attestation: Datastore,
    dfetch_cli: Process,
    patch_apply: Process,
) -> None:
    """Create datastores and wire all usage-model dataflows."""
    manifest_store, fetched_source, sbom_output, integrity_hash_record = (
        _make_usage_datastores_a(b_dev)
    )
    embedded_url_credential, metadata_store, patch_store = _make_usage_datastores_b(
        b_dev
    )
    _make_usage_vcs_dataflows(developer, dfetch_cli, manifest_store, remote_git_svn)
    _make_usage_archive_dataflows(dfetch_cli, archive_server)
    _make_usage_output_flows(
        dfetch_cli, fetched_source, metadata_store, sbom_output, embedded_url_credential
    )
    _make_usage_patch_and_build_flows(
        patch_apply, patch_store, fetched_source, consumer_build
    )
    _make_usage_extraction_elements_and_flows(b_dev, dfetch_cli)
    _make_usage_integrity_flows(
        dfetch_cli, manifest_store, integrity_hash_record, developer
    )
    _make_usage_gap_doc_flows(
        developer, patch_store, remote_git_svn, upstream_source_attestation
    )


def _make_usage_elements_and_flows(b_dev: Boundary, b_remote_vcs: Boundary) -> None:
    """Create all usage-model elements and wire their dataflows."""
    (
        developer,
        remote_git_svn,
        archive_server,
        consumer_build,
        upstream_source_attestation,
    ) = _make_usage_actors_and_external_entities(b_dev, b_remote_vcs)
    dfetch_cli, patch_apply = _make_usage_processes(b_dev)
    _make_usage_stores_and_flows(
        b_dev,
        developer,
        remote_git_svn,
        archive_server,
        consumer_build,
        upstream_source_attestation,
        dfetch_cli,
        patch_apply,
    )


def build_model() -> TM:
    """Construct and return the runtime-usage threat model."""
    TM.reset()
    apply_report_utils_patch()
    model = TM(
        "dfetch Runtime Usage",
        description=(
            "Threat model for dfetch.  "
            "Covers the post-install lifecycle: reading the manifest, fetching "
            "dependencies from VCS and archive sources, applying patches, writing "
            "vendored files, and generating reports (SBOM, SARIF, check output).  "
            "The installed dfetch package - produced by the supply chain in "
            "tm_supply_chain.py - is the entry point."
        ),
        isOrdered=True,
        mergeResponses=True,
        threatsFile=THREATS_FILE,
    )
    model.assumptions = make_usage_assumptions()
    b_dev, b_remote_vcs = _make_usage_boundaries()
    _make_usage_elements_and_flows(b_dev, b_remote_vcs)
    return model


# ── CONTROLS AND GAPS ────────────────────────────────────────────────────────

CONTROLS: list[Control] = [
    # ── Implemented controls ─────────────────────────────────────────────────
    Control(
        id="C-001",
        name="Path-traversal prevention",
        assets=["A-13", "A-20"],
        threats=["DFT-03"],
        reference="dfetch/util/util.py",
        assessment=ControlAssessment(
            risk="High", stride=["Tampering", "Elevation of Privilege"]
        ),
        description=(
            "``check_no_path_traversal()`` resolves both the candidate path and the "
            "destination root via ``os.path.realpath`` (symlink-aware), then rejects "
            "any path whose resolved prefix does not start with the resolved root.  "
            "Applied to every file copy and post-extraction symlink."
        ),
    ),
    Control(
        id="C-002",
        name="Decompression-bomb protection",
        assets=["A-20", "A-13"],
        threats=["DFT-09"],
        reference="dfetch/vcs/archive.py",
        assessment=ControlAssessment(risk="Medium", stride=["Denial of Service"]),
        description=(
            "Archives are rejected if the uncompressed size exceeds 500 MB or the "
            "member count exceeds 10 000."
        ),
    ),
    Control(
        id="C-003",
        name="Archive symlink validation",
        assets=["A-13"],
        threats=["DFT-03"],
        reference="dfetch/vcs/archive.py",
        assessment=ControlAssessment(
            risk="High", stride=["Tampering", "Elevation of Privilege"]
        ),
        description=(
            "Absolute and escaping (``..``) symlink targets are rejected for both "
            "TAR and ZIP.  A post-extraction walk validates all symlinks against "
            "the manifest root."
        ),
    ),
    Control(
        id="C-004",
        name="Archive member type checks",
        assets=["A-13", "A-20"],
        threats=["DFT-03"],
        reference="dfetch/vcs/archive.py",
        assessment=ControlAssessment(
            risk="Medium", stride=["Tampering", "Elevation of Privilege"]
        ),
        description=(
            "TAR and ZIP members of type device file or FIFO are rejected outright."
        ),
    ),
    Control(
        id="C-005",
        name="Integrity hash verification",
        assets=["A-13", "A-14"],
        threats=["DFT-01", "DFT-02", "DFT-05", "DFT-30"],
        reference="dfetch/vcs/integrity_hash.py",
        assessment=ControlAssessment(risk="Critical", stride=["Tampering", "Spoofing"]),
        description=(
            "SHA-256, SHA-384, and SHA-512 verified via ``hmac.compare_digest`` "
            "(constant-time comparison, resistant to timing attacks).  "
            "Primary defence against content substitution for archive dependencies.  "
            "Effectiveness is conditional on the hash field being present - see C-018."
        ),
    ),
    Control(
        id="C-006",
        name="Non-interactive VCS",
        assets=["A-16", "A-09"],
        threats=["DFT-06"],
        reference="dfetch/vcs/git.py, dfetch/vcs/svn.py",
        assessment=ControlAssessment(risk="Low", stride=["Spoofing"]),
        description=(
            "``GIT_TERMINAL_PROMPT=0``, ``BatchMode=yes`` for Git; "
            "``--non-interactive`` for SVN.  Credential prompts are suppressed to "
            "prevent interactive hijacking in CI."
        ),
    ),
    Control(
        id="C-007",
        name="Subprocess safety",
        assets=["A-22"],
        threats=["DFT-06"],
        reference="dfetch/util/cmdline.py",
        assessment=ControlAssessment(
            risk="High", stride=["Tampering", "Elevation of Privilege"]
        ),
        description=(
            "All external commands invoked with ``shell=False`` and list-form "
            "arguments - no shell-injection vector."
        ),
    ),
    Control(
        id="C-008",
        name="Manifest input validation",
        assets=["A-12"],
        threats=["DFT-04", "DFT-08"],
        reference="dfetch/manifest/schema.py",
        assessment=ControlAssessment(risk="High", stride=["Tampering"]),
        description=(
            r'StrictYAML schema with ``SAFE_STR = Regex(r"^[^\x00-\x1F\x7F-\x9F]*$")`` '
            "rejects control characters in all string fields."
        ),
    ),
    Control(
        id="C-034",
        name="Hash algorithm allowlist (SHA-256/384/512 only)",
        assets=["A-14"],
        threats=["DFT-30"],
        reference="dfetch/vcs/integrity_hash.py",
        assessment=ControlAssessment(
            status="implemented", risk="High", stride=["Tampering", "Spoofing"]
        ),
        description=(
            "``integrity_hash.py`` accepts only ``sha256:``, ``sha384:``, and "
            "``sha512:`` prefixes; any other algorithm prefix is rejected at parse "
            "time.  MD5 and SHA-1 are not accepted.  "
            "This directly mitigates DFT-30 (SLSA M2: exploit cryptographic hash "
            "collisions) by ensuring that integrity hashes, when present, use "
            "algorithms with no known practical collision attacks."
        ),
    ),
    # ── Gaps ─────────────────────────────────────────────────────────────────
    Control(
        id="C-018",
        name="Optional integrity hash",
        assets=["A-13", "A-14"],
        threats=["DFT-01", "DFT-02"],
        assessment=ControlAssessment(
            status="gap", risk="Critical", stride=["Tampering", "Spoofing"]
        ),
        description=(
            "``integrity.hash`` in the manifest is optional.  Archive dependencies "
            "without it have no content-authenticity guarantee.  Plain ``http://`` "
            "URLs receive no protection at all - neither transport nor content "
            "integrity is enforced."
        ),
    ),
    Control(
        id="C-019",
        name="No integrity mechanism for Git/SVN",
        assets=["A-13", "A-14"],
        threats=["DFT-02", "DFT-05"],
        assessment=ControlAssessment(
            status="gap", risk="High", stride=["Tampering", "Spoofing"]
        ),
        description=(
            "Git and SVN dependencies carry no equivalent to ``integrity.hash``.  "
            "Transport security (TLS or SSH) authenticates the server and channel "
            "but cannot detect content legitimately served by a compromised upstream.  "
            "Mutable references (branch, tag) can silently fetch different content "
            "after a force-push.  Pinning to an immutable commit SHA is the "
            "strongest available mitigation but is not currently enforced by dfetch."
        ),
    ),
    Control(
        id="C-020",
        name="No patch-file integrity",
        assets=["A-19", "A-13"],
        threats=["DFT-08", "DFT-03"],
        assessment=ControlAssessment(
            status="gap",
            risk="Critical",
            stride=["Tampering", "Elevation of Privilege"],
        ),
        description=(
            "Patch files referenced in the manifest carry no integrity hash.  A "
            "tampered or attacker-controlled patch file can write to arbitrary paths; "
            "path-safety is delegated entirely to ``patch-ng``'s internal implementation "
            "and is not independently verified by dfetch before application."
        ),
    ),
    Control(
        id="C-027",
        name="No redirect destination validation on archive downloads",
        assets=["A-13"],
        threats=["DFT-12"],
        assessment=ControlAssessment(
            status="gap", risk="High", stride=["Information Disclosure"]
        ),
        description=(
            "Archive downloads follow up to 10 HTTP 3xx redirects without "
            "validating the destination host against an allowlist.  "
            "A compromised or malicious archive server can redirect to an "
            "internal metadata endpoint (e.g. ``http://169.254.169.254/``) "
            "and dfetch will follow the redirect, potentially retrieving and "
            "writing internal credentials to disk.  Plain ``http://`` URLs "
            "amplify the risk - both the original request and the redirect "
            "are unencrypted.  "
            "Fix: reject redirects resolving to RFC-1918, loopback, or "
            "link-local ranges before following."
        ),
    ),
    Control(
        id="C-028",
        name="No denylist for security-sensitive destination paths",
        assets=["A-12", "A-13"],
        threats=["DFT-16"],
        assessment=ControlAssessment(
            status="gap", risk="High", stride=["Tampering", "Elevation of Privilege"]
        ),
        description=(
            "dfetch's path-traversal check (C-001) prevents writes outside "
            "the project root but does not maintain a denylist of "
            "security-sensitive within-root paths.  "
            "A manifest entry with ``dst: .github/workflows/`` would pass "
            "all current validation and silently overwrite CI pipeline "
            "definitions on the next ``dfetch update``.  "
            "Should warn or error when ``dst:`` resolves under known-sensitive "
            "prefixes (``.github/``, ``.circleci/``, ``Makefile``, etc.), "
            "or require all destinations to fall under an explicit vendor root."
        ),
    ),
    Control(
        id="C-029",
        name="Nested dependency references in vendored source are out of dfetch scope",
        assets=["A-13"],
        threats=["DFT-22"],
        assessment=ControlAssessment(
            status="implemented", risk="Low", stride=["Tampering"]
        ),
        description=(
            "DFT-22 (vendored content containing submodule or nested external "
            "references) describes threats that arise when the consuming build "
            "system processes build manifests embedded in vendored source "
            "(CMakeLists.txt, package.json, Cargo.toml, etc.).  "
            "Per the 'dfetch scope boundary' assumption, dfetch exports source "
            "files - it does not execute or resolve build-system instructions "
            "within them.  The responsibility for nested dependency resolution "
            "belongs to the manifest author and the consuming build system.  "
            "Consumers should audit vendored repositories for nested package "
            "manifests and treat all fetched source as untrusted."
        ),
    ),
    Control(
        id="C-030",
        name="No timeout or resource cap on VCS operations",
        assets=["A-20", "A-13"],
        threats=["DFT-09"],
        assessment=ControlAssessment(
            status="gap", risk="Low", stride=["Denial of Service"]
        ),
        description=(
            "Git clone and SVN export operations have no configurable timeout or "
            "maximum-transfer-size limit.  A pathological or compromised upstream "
            "can deliver arbitrarily large packfiles or working trees, causing "
            "disk exhaustion or prolonged CI runner occupation.  "
            "The 500 MB / 10k-member archive limits (C-002) do not apply to raw "
            "VCS checkouts.  Shallow clones (``--depth=1``) mitigate history "
            "size but do not bound working-tree size."
        ),
    ),
    Control(
        id="C-031",
        name="No verification of signed Git tags or Sigstore attestations",
        assets=["A-13", "A-14"],
        threats=["DFT-05", "DFT-21"],
        assessment=ControlAssessment(
            status="gap", risk="Medium", stride=["Spoofing", "Tampering"]
        ),
        description=(
            "dfetch does not verify GPG-signed Git tags or Sigstore tag attestations "
            "when resolving VCS dependencies.  Upstreams that publish signed releases "
            "offer a stronger authenticity guarantee than transport security alone, "
            "but dfetch cannot take advantage of it.  "
            "This is distinct from C-019: signing would authenticate which commit a "
            "tag names, not the content of the working tree.  "
            "For repositories that do publish signed releases, users should pin to "
            "the commit SHA recorded after manually running ``git tag -v``."
        ),
    ),
    Control(
        id="C-035",
        name="No upstream SLSA source level verification",
        assets=["A-09", "A-23"],
        threats=["DFT-31", "DFT-32"],
        assessment=ControlAssessment(
            status="gap", risk="Medium", stride=["Spoofing", "Tampering"]
        ),
        description=(
            "dfetch has no mechanism to check whether an upstream VCS source publishes "
            "or meets any SLSA source level.  The manifest schema has no field for "
            "declaring the expected SLSA source level of a dependency, and no tooling "
            "exists to fetch or verify Source Provenance Attestations or VSAs (A-23).  "
            "Consumers must manually assess the upstream's review, branch-protection, "
            "and ancestry-enforcement posture before trusting a dependency pin - this "
            "is undocumented and unenforced by dfetch.  "
            "DFT-31 (no VSA) and DFT-32 (no two-party review) both stem from this gap.  "
            "Fix: add an optional ``slsa_source_level:`` field to the manifest schema "
            "and implement VSA fetch-and-verify during ``dfetch update``."
        ),
    ),
    Control(
        id="C-036",
        name="No ancestry reachability check after VCS fetch",
        assets=["A-09", "A-13"],
        threats=["DFT-33"],
        assessment=ControlAssessment(status="gap", risk="Low", stride=["Tampering"]),
        description=(
            "dfetch does not verify whether a pinned commit SHA remains reachable "
            "from the upstream's current default branch after fetching.  An upstream "
            "that rewrites its history - interactive rebase, filter-branch, or "
            "force-push to main - can orphan a previously-audited SHA without "
            "triggering any alert.  SLSA Source Level 2 requires ancestry enforcement: "
            "the upstream must prevent such rewrites.  dfetch cannot enforce this on "
            "the upstream, but could detect lineage breaks post-fetch.  "
            "Fix: after fetching a commit SHA, run ``git merge-base --is-ancestor "
            "<sha> <remote>/<default-branch>`` and warn when the SHA is unreachable."
        ),
    ),
    Control(
        id="C-041",
        name="SVN externals not suppressed (--ignore-externals flag unused)",
        assets=["A-13", "A-09"],
        threats=["DFT-15"],
        assessment=ControlAssessment(status="gap", risk="High", stride=["Tampering"]),
        reference="dfetch/vcs/svn.py",
        description=(
            "``svn export`` is invoked without the ``--ignore-externals`` flag.  "
            "SVN repositories with ``svn:externals`` properties trigger undeclared "
            "fetches from third-party servers that bypass dfetch's manifest controls, "
            "integrity checks, and code-review audit trail.  Each external fetch is "
            "unverified and unavailable for inspection before vendoring."
        ),
    ),
    Control(
        id="C-042",
        name="setuid/setgid bits preserved during TAR extraction on Python < 3.11.4",
        assets=["A-13", "A-20"],
        threats=["DFT-14"],
        assessment=ControlAssessment(
            status="gap", risk="High", stride=["Tampering", "Elevation of Privilege"]
        ),
        reference="dfetch/vcs/archive.py",
        description=(
            "On Python versions prior to 3.11.4, ``tarfile.extractall()`` does not "
            "apply the ``filter='tar'`` parameter and preserves setuid, setgid, and "
            "sticky bits encoded in TAR member headers.  A malicious archive can "
            "introduce setuid-root binaries into the vendor directory; a later build "
            "step that invokes the extracted binary executes with elevated privileges.  "
            "This affects all dfetch users on Python < 3.11.4."
        ),
    ),
]

_USAGE_ASSET_IDS = {
    "A-09",
    "A-10",
    "A-11",
    "A-12",
    "A-13",
    "A-14",
    "A-15",
    "A-16",
    "A-17",
    "A-18",
    "A-19",
    "A-20",
    "A-21",
    "A-22",
    "A-23",
}
ASSET_CONTROLS: dict[str, list[Control]] = build_asset_controls_index(
    CONTROLS, _USAGE_ASSET_IDS
)

if __name__ == "__main__":
    run_model(build_model, CONTROLS)
