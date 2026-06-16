.. _control_register:

Control Register
================

All controls implemented by dfetch, sorted by ID. Risk-driven controls emerge
from the :doc:`threat models <security>`; compliance-only controls address CRA
requirements not independently surfaced by the risk analysis.

.. list-table::
   :header-rows: 1
   :widths: 8 40 16 36

   * - ID
     - Name
     - Type
     - Reference
   * - C-001
     - Path-traversal prevention
     - Risk-driven
     - dfetch/util/util.py
   * - C-002
     - Decompression-bomb protection
     - Risk-driven
     - dfetch/vcs/archive.py
   * - C-003
     - Archive symlink validation
     - Risk-driven
     - dfetch/vcs/archive.py
   * - C-004
     - Archive member type checks
     - Risk-driven
     - dfetch/vcs/archive.py
   * - C-005
     - Integrity hash verification
     - Risk-driven
     - dfetch/vcs/integrity_hash.py
   * - C-006
     - Non-interactive VCS
     - Risk-driven
     - dfetch/vcs/git.py, dfetch/vcs/svn.py
   * - C-007
     - Subprocess safety
     - Risk-driven
     - dfetch/util/cmdline.py
   * - C-008
     - Manifest input validation
     - Risk-driven
     - dfetch/manifest/schema.py
   * - C-009
     - Actions commit-SHA pinning
     - Risk-driven
     - .github/workflows/\*.yml
   * - C-010
     - OIDC trusted publishing
     - Risk-driven
     - .github/workflows/python-publish.yml
   * - C-011
     - Minimal workflow permissions
     - Risk-driven
     - .github/workflows/\*.yml
   * - C-012
     - persist-credentials: false
     - Risk-driven
     - .github/workflows/\*.yml
   * - C-013
     - Harden-runner (egress block)
     - Risk-driven
     - .github/workflows/\*.yml
   * - C-015
     - CodeQL static analysis
     - Risk-driven
     - .github/workflows/codeql-analysis.yml
   * - C-016
     - Dependency review
     - Risk-driven
     - .github/workflows/dependency-review.yml
   * - C-017
     - bandit security linter
     - Risk-driven
     - pyproject.toml
   * - C-021
     - Sigstore SBOM attestation
     - Risk-driven
     - —
   * - C-022
     - CycloneDX SBOM on PyPI
     - Risk-driven
     - —
   * - C-024
     - ``secrets: inherit`` scope
     - Risk-driven
     - —
   * - C-026
     - Consumer-side package provenance verification
     - Risk-driven
     - doc/howto/verify-integrity.rst
   * - C-032
     - Consumer attestation verification pins to release tag ref
     - Risk-driven
     - doc/howto/verify-integrity.rst
   * - C-033
     - Ref-scoped build cache keys isolate PR and release builds
     - Risk-driven
     - .github/workflows/build.yml
   * - C-034
     - Hash algorithm allowlist (SHA-256/384/512 only)
     - Risk-driven
     - dfetch/vcs/integrity_hash.py
   * - C-036
     - Persisted-metadata credential redaction
     - Risk-driven
     - dfetch/project/metadata.py
   * - C-037
     - SLSA Source Provenance Attestation of repository governance controls
     - Risk-driven
     - .github/workflows/source-provenance.yml
   * - C-038
     - Ancestry enforcement on dfetch main branch
     - Risk-driven
     - .github/workflows/
   * - C-039
     - Source build provenance and VSA attestations
     - Risk-driven
     - doc/howto/verify-integrity.rst
   * - C-040
     - Test result attestation on source archive
     - Risk-driven
     - .github/workflows/test.yml
   * - C-041
     - Winget manifest PRs reviewed by community maintainers
     - Risk-driven
     - .github/workflows/winget-publish.yml
   * - C-042
     - WINGET_TOKEN scoped to dedicated Winget environment
     - Risk-driven
     - .github/workflows/winget-publish.yml
   * - C-043
     - Release-gate CVE check on runtime dependencies
     - Compliance-only
     - .github/workflows/python-publish.yml (planned CI addition)
   * - C-044
     - Data minimisation policy
     - Compliance-only
     - doc/explanation/compliance_track.rst
   * - C-046
     - Exploit mitigation inventory
     - Compliance-only
     - doc/explanation/compliance_track.rst
