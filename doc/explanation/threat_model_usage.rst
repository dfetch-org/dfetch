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

Threat model for dfetch.  Covers the post-install lifecycle: reading the manifest, fetching dependencies from VCS and archive sources, applying patches, writing vendored files, and generating reports (SBOM, SARIF, check output).  The installed dfetch package - produced by the supply chain in tm_supply_chain.py - is the entry point.

Assumptions
-----------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Name
     - Description

   * - Trusted workstation
     - Developer workstations are trusted at dfetch invocation time.  A compromised workstation is outside the scope of this threat model.

   * - TLS delegated to client
     - TLS certificate validation is delegated to the OS trust store and the git / svn / urllib clients.  dfetch does not independently validate certificates.

   * - No persisted secrets
     - No runtime secrets are persisted to disk by dfetch itself.  VCS credentials are managed by the OS keychain, SSH agent, or CI secret store.

   * - Optional integrity hash
     - The ``integrity.hash`` field in the manifest is optional.  Archive dependencies without it have no content-authenticity guarantee beyond TLS transport, which is itself absent for plain ``http://`` URLs.

   * - Mutable VCS references
     - Branch- and tag-pinned Git dependencies are mutable references.  Upstream force-pushes silently change what is fetched without triggering a manifest diff.

   * - Manifest under code review
     - The manifest (``dfetch.yaml``) is under version control and subject to code review.  An adversary with write access to the manifest can redirect fetches to attacker-controlled sources; this threat is addressed at the code-review boundary, not within dfetch itself.

   * - dfetch scope boundary
     - dfetch is responsible only for its own security posture.  The security of fetched third-party source code is the responsibility of the manifest author who selects and pins each dependency.

   * - No HTTPS enforcement
     - HTTPS enforcement is the responsibility of the manifest author.  dfetch accepts ``http://``, ``svn://``, and other non-TLS scheme URLs as written - it does not upgrade or reject them.

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

   * - DF-01: Invoke dfetch command
     - Developer
     - A-22: dfetch Process
     -

   * - DF-02: Read manifest
     - A-12: dfetch Manifest
     - A-22: dfetch Process
     -

   * - DF-03a: Fetch VCS content - HTTPS/SSH
     - A-22: dfetch Process
     - A-09: Remote VCS Server
     - HTTPS / SSH

   * - DF-03b: Fetch VCS content - svn:// / http://
     - A-22: dfetch Process
     - A-09: Remote VCS Server
     - http / svn

   * - DF-04a: VCS content inbound - HTTPS/SSH
     - A-09: Remote VCS Server
     - A-22: dfetch Process
     - HTTPS / SSH

   * - DF-04b: VCS content inbound - svn:// / http://
     - A-09: Remote VCS Server
     - A-22: dfetch Process
     - http / svn

   * - DF-05a: Archive download request - HTTPS
     - A-22: dfetch Process
     - A-10: Archive HTTP Server
     - HTTPS

   * - DF-05b: Archive download request - HTTP
     - A-22: dfetch Process
     - A-10: Archive HTTP Server
     - HTTP

   * - DF-06a: Archive bytes - HTTPS
     - A-10: Archive HTTP Server
     - A-22: dfetch Process
     - HTTPS

   * - DF-06b: Archive bytes - HTTP (plaintext risk)
     - A-10: Archive HTTP Server
     - A-22: dfetch Process
     - HTTP

   * - DF-07: Write vendored files
     - A-22: dfetch Process
     - A-13: Fetched Source Code
     -

   * - DF-08: Write dependency metadata
     - A-22: dfetch Process
     - A-18: Dependency Metadata
     -

   * - DF-09: Write SBOM
     - A-22: dfetch Process
     - A-15: SBOM Output (CycloneDX)
     -

   * - DF-16: Read dependency metadata
     - A-18: Dependency Metadata
     - A-22: dfetch Process
     -

   * - DF-10: Read patch for application
     - A-19: Patch Files
     - Patch Application (patch-ng)
     -

   * - DF-10b: Write patched files to vendor directory
     - Patch Application (patch-ng)
     - A-13: Fetched Source Code
     -

   * - DF-15: Vendored source to build
     - A-13: Fetched Source Code
     - A-11: Consumer Build System
     -

   * - DF-11: Dispatch archive bytes to extraction
     - A-22: dfetch Process
     - Archive Extraction (tarfile / zipfile)
     -

   * - DF-12: Write extracted archive to temp dir
     - Archive Extraction (tarfile / zipfile)
     - A-20: Local VCS Cache (temp)
     -

   * - DF-13: Dispatch SVN export subprocess
     - A-22: dfetch Process
     - SVN Export (svn export)
     -

   * - DF-14: Write SVN export to temp dir
     - SVN Export (svn export)
     - A-20: Local VCS Cache (temp)
     -

   * - DF-17: Write audit / check reports
     - A-22: dfetch Process
     - A-21: Audit / Check Reports
     -


Data Dictionary
---------------

.. list-table::
   :header-rows: 1
   :widths: 25 55 20

   * - Name
     - Description
     - Classification

   * - A-16: VCS Credentials
     - SSH private keys, HTTPS Personal Access Tokens, SVN passwords.  Used to authenticate to private upstream repositories.  dfetch never persists these - managed by OS keychain, SSH agent, or CI secret store.
     - SECRET

   * - A-17: Embedded Credential in Remote URL
     - A VCS or archive URL that encodes a credential in the userinfo component (e.g. ``https://user:TOKEN@github.com/org/repo.git``).  dfetch writes ``remote_url`` verbatim to ``.dfetch_data.yaml`` after each successful fetch.  If the URL contains a Personal Access Token or password, that credential is persisted in plaintext and typically committed to VCS, where it becomes readable from every clone and CI checkout indefinitely.
     - SECRET


Actors
------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Name
     - Description

   * - Developer
     - Writes and reviews ``dfetch.yaml``; selects upstream sources, pins revisions, and optionally enables ``integrity.hash`` for archive dependencies.  Trusted at workstation invocation time.  Responsible for choosing trustworthy upstream sources and keeping pins current.


Boundaries
----------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Name
     - Description

   * - Local Developer Environment
     - Developer workstation or local CI runner.  Assumed trusted at invocation time.  Hosts the manifest (``dfetch.yaml``), vendor directory, dependency metadata (``.dfetch_data.yaml``), and patch files.

   * - Internet
     - All traffic crossing the local/remote boundary.  TLS enforcement is the responsibility of the OS and VCS clients; dfetch does not enforce HTTPS on manifest URLs.

   * - Remote VCS Infrastructure
     - Upstream Git and SVN servers (GitHub, GitLab, Gitea, self-hosted).  Not controlled by the dfetch project; content is untrusted until verified.

   * - Archive Content Space
     - Downloaded archive bytes before extraction and validation.  Decompression-bomb and path-traversal checks enforce this boundary during extraction.


Assets
------

.. list-table::
   :header-rows: 1
   :widths: 25 55 20

   * - Name
     - Description
     - Type

   * - A-09: Remote VCS Server
     - Upstream Git or SVN host: GitHub, GitLab, Gitea, self-hosted Git/SVN.  Not controlled by the dfetch project; content is untrusted until verified.  The SLSA source level of any upstream is unknown and unverified - dfetch does not check whether the upstream enforces branch protection, mandatory review, or ancestry enforcement, and no VSA is fetched alongside repository content (A-23).
     - ExternalEntity

   * - A-10: Archive HTTP Server
     - HTTP/HTTPS server serving ``.tar.gz``, ``.tgz``, ``.tar.bz2``, ``.tar.xz``, or ``.zip`` files.  CRITICAL: ``http://`` (non-TLS) URLs are accepted without enforcement of integrity hashes - the ``integrity.hash`` field is optional.
     - ExternalEntity

   * - A-23: Upstream Source Attestation (VSA)
     - SLSA Source Provenance Attestation or Verification Summary Attestation (VSA) that an upstream VCS host can publish for a specific revision, attesting that the source-level controls required by a given SLSA source level - branch protection, mandatory review, and ancestry enforcement - were applied.  CRITICAL: dfetch has no mechanism to request or verify source-level attestations and the manifest schema has no field to declare an expected SLSA source level.  In the absence of a VSA the consumer cannot cryptographically distinguish a well-governed upstream from one with no controls at all.
     - Datastore

   * - A-11: Consumer Build System
     - Build system that compiles fetched source code (A-13).  Not controlled by dfetch - it receives untrusted third-party source.
     - ExternalEntity

   * - A-22: dfetch Process
     - Python CLI entry point dispatching to: update, check, diff, add, remove, update-patch, format-patch, freeze, import, init, report, validate, environment.  Invokes Git and SVN as subprocesses (``shell=False``, list args).  Extracts archives with decompression-bomb limits and path-traversal checks.
     - Process

   * - Patch Application (patch-ng)
     - Invokes ``patch-ng`` to apply unified-diff files from ``patch:`` references in the manifest.  Path safety is delegated entirely to ``patch-ng``'s internal implementation - dfetch does not independently sanitise patch-file destination paths before handing off to the library.
     - Process

   * - A-12: dfetch Manifest
     - ``dfetch.yaml`` - declares all upstream sources (URL/VCS type), version pins (branch / tag / revision / SHA), dst paths, patch references, and optional integrity hashes.  Tampering redirects fetches to attacker-controlled sources.  RISK: ``integrity.hash`` is Optional in schema - archive deps can be declared without any content-authenticity guarantee.
     - Datastore

   * - A-13: Fetched Source Code
     - Third-party source code written to the ``dst:`` path after extraction / checkout.  Becomes a direct build input for the consuming project.  A compromised upstream or MITM can inject malicious code that executes in the consumer's build system, test runner, or production binary.
     - Datastore

   * - A-14: Integrity Hash Record
     - ``integrity.hash:`` field in ``dfetch.yaml`` (sha256/sha384/sha512:<hex>).  Primary trust anchor for archive-type dependencies when present.  Verified via ``hmac.compare_digest`` (constant-time).  Field is optional - absence disables content verification for archives (C-018).  Git and SVN have no equivalent; they rely entirely on transport security (C-019).
     - Datastore

   * - A-15: SBOM Output (CycloneDX)
     - CycloneDX JSON/XML produced by ``dfetch report -t sbom``.  Enumerates vendored components with PURL, license, and hash.  Falsification hides actual dependencies from downstream CVE scanners.  NOTE: this SBOM covers vendored deps only - dfetch itself has a separate machine-readable SBOM published on PyPI (see A-04 in tm_supply_chain.py).
     - Datastore

   * - A-18: Dependency Metadata
     - ``.dfetch_data.yaml`` files written after each successful fetch.  Contains: remote_url, revision/branch/tag, hash, last-fetch timestamp.  Read by ``dfetch check`` to detect outdated deps.  Tampering can suppress update notifications - an attacker who controls the local filesystem can silently mask a compromised vendored dep.
     - Datastore

   * - A-19: Patch Files
     - Unified-diff ``.patch`` files referenced by ``patch:`` in ``dfetch.yaml``.  Applied by ``patch-ng`` after fetch.  A malicious patch can write to arbitrary destination paths - dfetch's path-traversal guards apply to archive extraction but ``patch-ng``'s own path safety depends on its internal implementation.  Patch files are not integrity-verified (no hash in manifest schema).
     - Datastore

   * - Archive Extraction (tarfile / zipfile)
     - Decompresses and extracts TAR (.tar.gz/.tgz/.tar.bz2/.tar.xz) and ZIP archives to a temporary directory.  Pre-extraction checks validate decompression-bomb limits, path traversal, symlinks, hardlinks, device files, and FIFOs.  On Python ≥ 3.11.4: ``filter='tar'`` strips setuid/setgid bits during extraction.  On Python < 3.11.4: ``extractall()`` is called without a filter - setuid, setgid, and sticky bits from TAR member headers are preserved on the extracted files, allowing a malicious archive to introduce setuid-root binaries into the vendor directory.
     - Process

   * - SVN Export (svn export)
     - Runs ``svn export --non-interactive --force`` to check out SVN dependencies.  The ``--ignore-externals`` flag is NOT passed.  SVN repositories with ``svn:externals`` properties will trigger additional fetches from third-party SVN servers not declared in ``dfetch.yaml``.  These undeclared fetches bypass dfetch's manifest controls: no integrity hash, no metadata record, and no code review of the external URL.
     - Process

   * - A-20: Local VCS Cache (temp)
     - Temporary directory used during git-clone / svn-checkout / archive extraction.  Deleted after content is copied to dst.  Path-traversal attacks targeting this space are mitigated by ``check_no_path_traversal()`` and post-extraction symlink walks.
     - Datastore

   * - A-21: Audit / Check Reports
     - SARIF, Jenkins warnings-ng, Code Climate JSON produced by ``dfetch check``.  Falsification hides vulnerabilities from downstream security dashboards.
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
   * - C-001
     - Path-traversal prevention
     - High
     - Tampering, Elevation of Privilege
     - DFT-03
     - Mitigates: ``check_no_path_traversal()`` resolves both the candidate path and the destination root via ``os.path.realpath`` (symlink-aware), then rejects any path whose resolved prefix does not start with the resolved root.  Applied to every file copy and post-extraction symlink.  ``dfetch/util/util.py``
   * - C-002
     - Decompression-bomb protection
     - Medium
     - Denial of Service
     - DFT-09
     - Mitigates: Archives are rejected if the uncompressed size exceeds 500 MB or the member count exceeds 10 000.  ``dfetch/vcs/archive.py``
   * - C-003
     - Archive symlink validation
     - High
     - Tampering, Elevation of Privilege
     - DFT-03
     - Mitigates: Absolute and escaping (``..``) symlink targets are rejected for both TAR and ZIP.  A post-extraction walk validates all symlinks against the manifest root.  ``dfetch/vcs/archive.py``
   * - C-004
     - Archive member type checks
     - Medium
     - Tampering, Elevation of Privilege
     - DFT-03
     - Mitigates: TAR and ZIP members of type device file or FIFO are rejected outright.  ``dfetch/vcs/archive.py``
   * - C-005
     - Integrity hash verification
     - Critical
     - Tampering, Spoofing
     - DFT-01, DFT-02, DFT-05, DFT-30
     - Mitigates: SHA-256, SHA-384, and SHA-512 verified via ``hmac.compare_digest`` (constant-time comparison, resistant to timing attacks).  Primary defence against content substitution for archive dependencies.  Effectiveness is conditional on the hash field being present - see C-018.  ``dfetch/vcs/integrity_hash.py``
   * - C-006
     - Non-interactive VCS
     - Low
     - Spoofing
     - DFT-06
     - Mitigates: ``GIT_TERMINAL_PROMPT=0``, ``BatchMode=yes`` for Git; ``--non-interactive`` for SVN.  Credential prompts are suppressed to prevent interactive hijacking in CI.  ``dfetch/vcs/git.py, dfetch/vcs/svn.py``
   * - C-007
     - Subprocess safety
     - High
     - Tampering, Elevation of Privilege
     - DFT-06
     - Mitigates: All external commands invoked with ``shell=False`` and list-form arguments - no shell-injection vector.  ``dfetch/util/cmdline.py``
   * - C-008
     - Manifest input validation
     - High
     - Tampering
     - DFT-04, DFT-08
     - Mitigates: StrictYAML schema with ``SAFE_STR = Regex(r"^[^\x00-\x1F\x7F-\x9F]*$")`` rejects control characters in all string fields.  ``dfetch/manifest/schema.py``
   * - C-034
     - Hash algorithm allowlist (SHA-256/384/512 only)
     - High
     - Tampering, Spoofing
     - DFT-30
     - Mitigates: ``integrity_hash.py`` accepts only ``sha256:``, ``sha384:``, and ``sha512:`` prefixes; any other algorithm prefix is rejected at parse time.  MD5 and SHA-1 are not accepted.  This directly mitigates DFT-30 (SLSA M2: exploit cryptographic hash collisions) by ensuring that integrity hashes, when present, use algorithms with no known practical collision attacks.  ``dfetch/vcs/integrity_hash.py``
   * - C-029
     - Nested dependency references in vendored source are out of dfetch scope
     - Low
     - Tampering
     - DFT-22
     - Mitigates: DFT-22 (vendored content containing submodule or nested external references) describes threats that arise when the consuming build system processes build manifests embedded in vendored source (CMakeLists.txt, package.json, Cargo.toml, etc.).  Per the 'dfetch scope boundary' assumption, dfetch exports source files - it does not execute or resolve build-system instructions within them.  The responsibility for nested dependency resolution belongs to the manifest author and the consuming build system.  Consumers should audit vendored repositories for nested package manifests and treat all fetched source as untrusted.


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
   * - C-018
     - Optional integrity hash
     - Critical
     - Tampering, Spoofing
     - DFT-01, DFT-02
     - Affects: ``integrity.hash`` in the manifest is optional.  Archive dependencies without it have no content-authenticity guarantee.  Plain ``http://`` URLs receive no protection at all - neither transport nor content integrity is enforced.
   * - C-019
     - No integrity mechanism for Git/SVN
     - High
     - Tampering, Spoofing
     - DFT-02, DFT-05
     - Affects: Git and SVN dependencies carry no equivalent to ``integrity.hash``.  Transport security (TLS or SSH) authenticates the server and channel but cannot detect content legitimately served by a compromised upstream.  Mutable references (branch, tag) can silently fetch different content after a force-push.  Pinning to an immutable commit SHA is the strongest available mitigation but is not currently enforced by dfetch.
   * - C-020
     - No patch-file integrity
     - Critical
     - Tampering, Elevation of Privilege
     - DFT-08, DFT-03
     - Affects: Patch files referenced in the manifest carry no integrity hash.  A tampered or attacker-controlled patch file can write to arbitrary paths; path-safety is delegated entirely to ``patch-ng``'s internal implementation and is not independently verified by dfetch before application.
   * - C-027
     - No redirect destination validation on archive downloads
     - High
     - Information Disclosure
     - DFT-12
     - Affects: Archive downloads follow up to 10 HTTP 3xx redirects without validating the destination host against an allowlist.  A compromised or malicious archive server can redirect to an internal metadata endpoint (e.g. ``http://169.254.169.254/``) and dfetch will follow the redirect, potentially retrieving and writing internal credentials to disk.  Plain ``http://`` URLs amplify the risk - both the original request and the redirect are unencrypted.  Fix: reject redirects resolving to RFC-1918, loopback, or link-local ranges before following.
   * - C-028
     - No denylist for security-sensitive destination paths
     - High
     - Tampering, Elevation of Privilege
     - DFT-16
     - Affects: dfetch's path-traversal check (C-001) prevents writes outside the project root but does not maintain a denylist of security-sensitive within-root paths.  A manifest entry with ``dst: .github/workflows/`` would pass all current validation and silently overwrite CI pipeline definitions on the next ``dfetch update``.  Should warn or error when ``dst:`` resolves under known-sensitive prefixes (``.github/``, ``.circleci/``, ``Makefile``, etc.), or require all destinations to fall under an explicit vendor root.
   * - C-030
     - No timeout or resource cap on VCS operations
     - Low
     - Denial of Service
     - DFT-09
     - Affects: Git clone and SVN export operations have no configurable timeout or maximum-transfer-size limit.  A pathological or compromised upstream can deliver arbitrarily large packfiles or working trees, causing disk exhaustion or prolonged CI runner occupation.  The 500 MB / 10k-member archive limits (C-002) do not apply to raw VCS checkouts.  Shallow clones (``--depth=1``) mitigate history size but do not bound working-tree size.
   * - C-031
     - No verification of signed Git tags or Sigstore attestations
     - Medium
     - Spoofing, Tampering
     - DFT-05, DFT-21
     - Affects: dfetch does not verify GPG-signed Git tags or Sigstore tag attestations when resolving VCS dependencies.  Upstreams that publish signed releases offer a stronger authenticity guarantee than transport security alone, but dfetch cannot take advantage of it.  This is distinct from C-019: signing would authenticate which commit a tag names, not the content of the working tree.  For repositories that do publish signed releases, users should pin to the commit SHA recorded after manually running ``git tag -v``.
   * - C-035
     - No upstream SLSA source level verification
     - Medium
     - Spoofing, Tampering
     - DFT-31, DFT-32
     - Affects: dfetch has no mechanism to check whether an upstream VCS source publishes or meets any SLSA source level.  The manifest schema has no field for declaring the expected SLSA source level of a dependency, and no tooling exists to fetch or verify Source Provenance Attestations or VSAs (A-23).  Consumers must manually assess the upstream's review, branch-protection, and ancestry-enforcement posture before trusting a dependency pin - this is undocumented and unenforced by dfetch.  DFT-31 (no VSA) and DFT-32 (no two-party review) both stem from this gap.  Fix: add an optional ``slsa_source_level:`` field to the manifest schema and implement VSA fetch-and-verify during ``dfetch update``.
   * - C-036
     - No ancestry reachability check after VCS fetch
     - Low
     - Tampering
     - DFT-33
     - Affects: dfetch does not verify whether a pinned commit SHA remains reachable from the upstream's current default branch after fetching.  An upstream that rewrites its history - interactive rebase, filter-branch, or force-push to main - can orphan a previously-audited SHA without triggering any alert.  SLSA Source Level 2 requires ancestry enforcement: the upstream must prevent such rewrites.  dfetch cannot enforce this on the upstream, but could detect lineage breaks post-fetch.  Fix: after fetching a commit SHA, run ``git merge-base --is-ancestor <sha> <remote>/<default-branch>`` and warn when the SHA is unreachable.
   * - C-041
     - SVN externals not suppressed (--ignore-externals flag unused)
     - High
     - Tampering
     - DFT-15
     - Affects: ``svn export`` is invoked without the ``--ignore-externals`` flag.  SVN repositories with ``svn:externals`` properties trigger undeclared fetches from third-party servers that bypass dfetch's manifest controls, integrity checks, and code-review audit trail.  Each external fetch is unverified and unavailable for inspection before vendoring.  ``dfetch/vcs/svn.py``
   * - C-042
     - setuid/setgid bits preserved during TAR extraction on Python < 3.11.4
     - High
     - Tampering, Elevation of Privilege
     - DFT-14
     - Affects: On Python versions prior to 3.11.4, ``tarfile.extractall()`` does not apply the ``filter='tar'`` parameter and preserves setuid, setgid, and sticky bits encoded in TAR member headers.  A malicious archive can introduce setuid-root binaries into the vendor directory; a later build step that invokes the extracted binary executes with elevated privileges.  This affects all dfetch users on Python < 3.11.4.  ``dfetch/vcs/archive.py``
