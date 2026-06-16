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
   * - .. _c-001:

       C-001
     - Path-traversal prevention
     - Risk-driven
     - `dfetch/util/util.py <https://github.com/dfetch-org/dfetch/blob/main/dfetch/util/util.py>`_
   * - .. _c-002:

       C-002
     - Decompression-bomb protection
     - Risk-driven
     - `dfetch/vcs/archive.py <https://github.com/dfetch-org/dfetch/blob/main/dfetch/vcs/archive.py>`_
   * - .. _c-003:

       C-003
     - Archive symlink validation
     - Risk-driven
     - `dfetch/vcs/archive.py <https://github.com/dfetch-org/dfetch/blob/main/dfetch/vcs/archive.py>`_
   * - .. _c-004:

       C-004
     - Archive member type checks
     - Risk-driven
     - `dfetch/vcs/archive.py <https://github.com/dfetch-org/dfetch/blob/main/dfetch/vcs/archive.py>`_
   * - .. _c-005:

       C-005
     - Integrity hash verification
     - Risk-driven
     - `dfetch/vcs/integrity_hash.py <https://github.com/dfetch-org/dfetch/blob/main/dfetch/vcs/integrity_hash.py>`_
   * - .. _c-006:

       C-006
     - Non-interactive VCS
     - Risk-driven
     - `dfetch/vcs/git.py <https://github.com/dfetch-org/dfetch/blob/main/dfetch/vcs/git.py>`_,
       `dfetch/vcs/svn.py <https://github.com/dfetch-org/dfetch/blob/main/dfetch/vcs/svn.py>`_
   * - .. _c-007:

       C-007
     - Subprocess safety
     - Risk-driven
     - `dfetch/util/cmdline.py <https://github.com/dfetch-org/dfetch/blob/main/dfetch/util/cmdline.py>`_
   * - .. _c-008:

       C-008
     - Manifest input validation
     - Risk-driven
     - `dfetch/manifest/schema.py <https://github.com/dfetch-org/dfetch/blob/main/dfetch/manifest/schema.py>`_
   * - .. _c-009:

       C-009
     - Actions commit-SHA pinning
     - Risk-driven
     - `.github/workflows/ <https://github.com/dfetch-org/dfetch/tree/main/.github/workflows>`_
   * - .. _c-010:

       C-010
     - OIDC trusted publishing
     - Risk-driven
     - `.github/workflows/python-publish.yml <https://github.com/dfetch-org/dfetch/blob/main/.github/workflows/python-publish.yml>`_
   * - .. _c-011:

       C-011
     - Minimal workflow permissions
     - Risk-driven
     - `.github/workflows/ <https://github.com/dfetch-org/dfetch/tree/main/.github/workflows>`_
   * - .. _c-012:

       C-012
     - persist-credentials: false
     - Risk-driven
     - `.github/workflows/ <https://github.com/dfetch-org/dfetch/tree/main/.github/workflows>`_
   * - .. _c-013:

       C-013
     - Harden-runner (egress block)
     - Risk-driven
     - `.github/workflows/ <https://github.com/dfetch-org/dfetch/tree/main/.github/workflows>`_
   * - .. _c-015:

       C-015
     - CodeQL static analysis
     - Risk-driven
     - `.github/workflows/codeql-analysis.yml <https://github.com/dfetch-org/dfetch/blob/main/.github/workflows/codeql-analysis.yml>`_
   * - .. _c-016:

       C-016
     - Dependency review
     - Risk-driven
     - `.github/workflows/dependency-review.yml <https://github.com/dfetch-org/dfetch/blob/main/.github/workflows/dependency-review.yml>`_
   * - .. _c-017:

       C-017
     - bandit security linter
     - Risk-driven
     - `pyproject.toml <https://github.com/dfetch-org/dfetch/blob/main/pyproject.toml>`_
   * - .. _c-021:

       C-021
     - Sigstore SBOM attestation
     - Risk-driven
     - —
   * - .. _c-022:

       C-022
     - CycloneDX SBOM on PyPI
     - Risk-driven
     - —
   * - .. _c-024:

       C-024
     - ``secrets: inherit`` scope
     - Risk-driven
     - —
   * - .. _c-026:

       C-026
     - Consumer-side package provenance verification
     - Risk-driven
     - :doc:`../howto/verify-integrity`
   * - .. _c-032:

       C-032
     - Consumer attestation verification pins to release tag ref
     - Risk-driven
     - :doc:`../howto/verify-integrity`
   * - .. _c-033:

       C-033
     - Ref-scoped build cache keys isolate PR and release builds
     - Risk-driven
     - `.github/workflows/build.yml <https://github.com/dfetch-org/dfetch/blob/main/.github/workflows/build.yml>`_
   * - .. _c-034:

       C-034
     - Hash algorithm allowlist (SHA-256/384/512 only)
     - Risk-driven
     - `dfetch/vcs/integrity_hash.py <https://github.com/dfetch-org/dfetch/blob/main/dfetch/vcs/integrity_hash.py>`_
   * - .. _c-036:

       C-036
     - Persisted-metadata credential redaction
     - Risk-driven
     - `dfetch/project/metadata.py <https://github.com/dfetch-org/dfetch/blob/main/dfetch/project/metadata.py>`_
   * - .. _c-037:

       C-037
     - SLSA Source Provenance Attestation of repository governance controls
     - Risk-driven
     - `.github/workflows/source-provenance.yml <https://github.com/dfetch-org/dfetch/blob/main/.github/workflows/source-provenance.yml>`_
   * - .. _c-038:

       C-038
     - Ancestry enforcement on dfetch main branch
     - Risk-driven
     - `.github/workflows/ <https://github.com/dfetch-org/dfetch/tree/main/.github/workflows>`_
   * - .. _c-039:

       C-039
     - Source build provenance and VSA attestations
     - Risk-driven
     - :doc:`../howto/verify-integrity`
   * - .. _c-040:

       C-040
     - Test result attestation on source archive
     - Risk-driven
     - `.github/workflows/test.yml <https://github.com/dfetch-org/dfetch/blob/main/.github/workflows/test.yml>`_
   * - .. _c-041:

       C-041
     - Winget manifest PRs reviewed by community maintainers
     - Risk-driven
     - `.github/workflows/winget-publish.yml <https://github.com/dfetch-org/dfetch/blob/main/.github/workflows/winget-publish.yml>`_
   * - .. _c-042:

       C-042
     - WINGET_TOKEN scoped to dedicated Winget environment
     - Risk-driven
     - `.github/workflows/winget-publish.yml <https://github.com/dfetch-org/dfetch/blob/main/.github/workflows/winget-publish.yml>`_
   * - .. _c-043:

       C-043
     - Release-gate CVE check on runtime dependencies
     - Compliance-only
     - `.github/workflows/python-publish.yml <https://github.com/dfetch-org/dfetch/blob/main/.github/workflows/python-publish.yml>`_ (Audit runtime dependencies for CVEs step)
   * - .. _c-044:

       C-044
     - Data minimisation policy
     - Compliance-only
     - :doc:`compliance_track`
   * - .. _c-046:

       C-046
     - Exploit mitigation inventory
     - Compliance-only
     - :doc:`compliance_track`
