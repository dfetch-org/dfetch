"""Control register data — no pytm dependency.

All implemented security controls for dfetch, split by threat model scope:

* ``SC_CONTROLS``    — supply-chain controls (C-009 … C-042)
* ``USAGE_CONTROLS`` — runtime-usage controls (C-001 … C-045)

This module is intentionally pytm-free so that ``compliance.py`` and other
tooling can import the full control register without requiring pytm to be
installed.  The threat-model files (``tm_supply_chain.py``, ``tm_usage.py``)
re-export the same lists via ``CONTROLS = SC_CONTROLS / USAGE_CONTROLS``.
"""

from dataclasses import dataclass, field


@dataclass
class Control:
    """An implemented security control."""

    id: str
    name: str
    description: str
    assets: list[str] = field(default_factory=list)
    threats: list[str] = field(default_factory=list)
    reference: str = ""

    def to_pytm(self) -> str:
        """Return a human-readable label used in traceability comments."""
        return f"[{self.id}] {self.name}"


# ── Supply-chain controls (C-009 … C-042) ────────────────────────────────────

SC_CONTROLS: list[Control] = [
    Control(
        id="C-009",
        name="Actions commit-SHA pinning",
        assets=["A-01", "A-02"],
        threats=["DFT-07"],
        reference=".github/workflows/*.yml",
        description=(
            "All third-party GitHub Actions are pinned to a full commit SHA "
            "(``@<40-hex>``), preventing tag-mutable supply-chain substitution."
        ),
    ),
    Control(
        id="C-010",
        name="OIDC trusted publishing",
        assets=["A-05", "A-03"],
        threats=["DFT-07"],
        reference=".github/workflows/python-publish.yml",
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
        description=(
            "``persist-credentials: false`` is set on almost all checkout steps across "
            "all workflows that run on a runner.  "
            "Two exceptions are intentional: ``release.yml`` (needs write access to push "
            "release assets) and the ``attest-source-governance`` job in "
            "``source-provenance.yml`` (the ``slsa_with_provenance`` action requires "
            "repository write access).  "
            "All other checkout steps suppress credential persistence."
        ),
    ),
    Control(
        id="C-013",
        name="Harden-runner (egress block)",
        assets=["A-01", "A-02"],
        threats=["DFT-07", "DFT-29"],
        reference=".github/workflows/*.yml",
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
        description=(
            "``bandit -r dfetch`` runs in CI to detect common Python security issues."
        ),
    ),
    Control(
        id="C-021",
        name="Sigstore SBOM attestation",
        assets=["A-03"],
        threats=["DFT-05"],
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
        description=(
            "A CycloneDX SBOM is generated during the build and published "
            "alongside the PyPI release, satisfying CRA Article 13 requirements."
        ),
    ),
    Control(
        id="C-024",
        name="Explicit secret forwarding",
        assets=["A-01", "A-05"],
        threats=["DFT-07"],
        reference=".github/workflows/ci.yml",
        description=(
            "``ci.yml`` explicitly names only the secrets each child workflow "
            "requires (``CODACY_PROJECT_TOKEN`` → ``test.yml``; "
            "``GH_DFETCH_ORG_DEPLOY`` → ``docs.yml``); all other repository "
            "secrets are not forwarded.  ``secrets: inherit`` is deliberately "
            "not used so that malicious PR steps cannot exfiltrate unrelated secrets."
        ),
    ),
    Control(
        id="C-026",
        name="Consumer-side package provenance verification",
        assets=["A-03"],
        threats=["DFT-17", "DFT-25"],
        reference="doc/howto/verify-integrity.rst",
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
        reference="doc/howto/verify-integrity.rst",
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
    Control(
        id="C-041",
        name="Winget manifest PRs reviewed by community maintainers",
        assets=["A-09"],
        threats=["DFT-35"],
        reference=".github/workflows/winget-publish.yml",
        description=(
            "Manifest update PRs submitted to ``microsoft/winget-pkgs`` by "
            "``winget-publish.yml`` go through the standard Winget community review "
            "process before merging.  "
            "``microsoft/winget-pkgs`` maintainers verify the publisher identity and "
            "inspect manifest changes including installer URLs and hashes.  "
            "This provides a manual review gate between a fraudulent PR submission "
            "and consumer exposure.  "
            "Residual risk: a reviewer who approves without independently verifying "
            "the installer URL origin could merge a fraudulent manifest."
        ),
    ),
    Control(
        id="C-042",
        name="WINGET_TOKEN scoped to dedicated Winget environment",
        assets=["A-10"],
        threats=["DFT-34"],
        reference=".github/workflows/winget-publish.yml",
        description=(
            "``WINGET_TOKEN`` is stored in the ``winget`` GitHub Actions deployment "
            "environment, limiting its exposure: the PAT is only injected into "
            "workflows that explicitly reference that environment.  "
            "Only ``winget-publish.yml`` references the ``winget`` environment, "
            "so the PAT is not available to other workflows.  "
            "Residual risk: unlike PyPI which uses OIDC (A-05, no stored long-lived "
            "token), Winget does not support OIDC trusted publishing; the PAT must "
            "be stored and rotated manually (DFT-34)."
        ),
    ),
]

# ── Runtime-usage controls (C-001 … C-045) ───────────────────────────────────

USAGE_CONTROLS: list[Control] = [
    Control(
        id="C-001",
        name="Path-traversal prevention",
        assets=["A-13", "A-20"],
        threats=["DFT-03"],
        reference="dfetch/util/util.py",
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
        description=(
            "TAR and ZIP members of type device file or FIFO are rejected outright."
        ),
    ),
    Control(
        id="C-005",
        name="Integrity hash verification",
        assets=["A-12", "A-13"],
        threats=["DFT-01", "DFT-02", "DFT-05", "DFT-30"],
        reference="dfetch/vcs/integrity_hash.py",
        description=(
            "SHA-256, SHA-384, and SHA-512 verified via ``hmac.compare_digest`` "
            "(constant-time comparison, resistant to timing attacks).  "
            "Primary defence against content substitution for archive dependencies.  "
            "Effectiveness is conditional on the hash field being present."
        ),
    ),
    Control(
        id="C-006",
        name="Non-interactive VCS",
        assets=["A-16", "A-09"],
        threats=["DFT-06"],
        reference="dfetch/vcs/git.py, dfetch/vcs/svn.py",
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
        description=(
            r'StrictYAML schema with ``SAFE_STR = Regex(r"^[^\x00-\x1F\x7F-\x9F]*$")`` '
            "rejects control characters in all string fields."
        ),
    ),
    Control(
        id="C-034",
        name="Hash algorithm allowlist (SHA-256/384/512 only)",
        assets=["A-12"],
        threats=["DFT-30"],
        reference="dfetch/vcs/integrity_hash.py",
        description=(
            "``integrity_hash.py`` accepts only ``sha256:``, ``sha384:``, and "
            "``sha512:`` prefixes; any other algorithm prefix is rejected at parse "
            "time.  MD5 and SHA-1 are not accepted.  "
            "This directly mitigates DFT-30 (SLSA M2: exploit cryptographic hash "
            "collisions) by ensuring that integrity hashes, when present, use "
            "algorithms with no known practical collision attacks."
        ),
    ),
    Control(
        id="C-036",
        name="Persisted-metadata credential redaction",
        assets=["A-17", "A-18"],
        threats=["DFT-13"],
        reference="dfetch/project/metadata.py",
        description=(
            "``Metadata.dump()`` rebuilds the netloc of every persisted URL from "
            "``parsed.hostname`` and ``parsed.port`` via ``urllib.parse.urlsplit`` / "
            "``urlunsplit``, dropping any ``user:password@`` userinfo before writing "
            "``.dfetch_data.yaml``.  The same stripper is applied to each "
            "``dependencies[].remote_url`` entry (git submodule, svn:external) so a "
            "credential in a nested upstream URL also never reaches disk.  The "
            "in-memory ``Metadata`` object held by the running command keeps the "
            "original URL — only the on-disk representation is redacted, so an "
            "in-flight authenticated fetch is unaffected."
        ),
    ),
    Control(
        id="C-045",
        name="Plaintext transport detection",
        assets=["A-09", "A-22"],
        threats=["DFT-26"],
        reference="dfetch/manifest/project.py, dfetch/project/subproject.py",
        description=(
            "``plaintext_warning()`` (``dfetch/manifest/project.py``) inspects the "
            "resolved remote URL immediately before each VCS command is issued "
            "(inside the ``check_for_update`` and ``update`` spinners in "
            "``subproject.py``).  If the scheme is ``http://``, ``git://``, or "
            "``svn://``, a visible warning is emitted naming the redacted URL "
            "(credentials stripped from the userinfo component) and recommending "
            "``https://`` or ``svn+ssh://``.  "
            "Detection only — dfetch still proceeds with the plaintext connection; "
            "the control raises user awareness but does not enforce scheme selection."
        ),
    ),
]
