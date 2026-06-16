
Glossary
========

.. glossary::
   :sorted:

   Archive
      A compressed file (``tar.gz``, ``tgz``, ``tar.bz2``, ``tar.xz``, or ``zip``)
      served over HTTP, HTTPS, or a ``file://`` URL used as a dependency source.
      Declare it with ``vcs: archive`` in the manifest.  Unlike Git or SVN
      projects, archives carry no VCS history; use the :term:`Integrity` field
      to verify the download cryptographically.

   Destination
      The local path, relative to the manifest file, where *Dfetch* places the
      fetched files of a subproject.  Set with the ``dst:`` attribute; defaults
      to the project ``name:`` when omitted.

   Freeze
      The operation performed by ``dfetch freeze`` that replaces every loose
      ``branch:`` or open ``tag:`` reference in the manifest with the exact
      revision that is currently fetched.  Produces a fully reproducible
      manifest where every dependency is pinned to a specific commit or
      archive URL.

   Integrity
      An optional cryptographic hash declared in the manifest under
      ``integrity.hash:`` for :term:`Archive` dependencies.  Format is
      ``<algorithm>:<hex-digest>`` (e.g. ``sha256:e3b0c4…``).  *Dfetch*
      verifies the downloaded archive against this hash before extracting
      it, and records it in the generated :term:`SBOM`.

   Manifest
      The ``dfetch.yaml`` file that describes all dependencies of a
      :term:`Superproject`.  It lists :term:`Remote` sources and the
      :term:`Subproject` entries to fetch, together with their version pins,
      source paths, and patches.  *Dfetch* searches upward from the current
      directory to locate the manifest automatically.

   Metadata
      The ``.dfetch_data.yaml`` file that *Dfetch* writes inside each fetched
      :term:`Subproject` directory.  It records the URL, VCS type, and exact
      revision that is currently present, allowing *Dfetch* to detect
      out-of-date or locally modified dependencies without re-contacting the
      remote.

   Patch
      A ``.patch`` file that captures local modifications to a vendored
      :term:`Subproject`.  Declared with the ``patch:`` attribute in the
      manifest, patches are automatically re-applied by ``dfetch update``
      after each upstream fetch.  Created with ``dfetch diff`` and reformatted
      for upstream submission with ``dfetch format-patch``.

   Remote
      A named entry in the manifest that provides a common ``url-base`` for
      multiple projects.  Instead of repeating a full URL for every
      :term:`Subproject`, projects can reference the remote by name and supply
      only their ``repo-path:``.

   Repo-path
      The path appended to a :term:`Remote`'s ``url-base`` to form the full
      repository URL of a :term:`Subproject`.  Use it together with a
      ``remote:`` reference to avoid repeating the URL base across many
      entries.

   SBOM
      Software Bill of Materials — a machine-readable inventory of software
      components and their licences.  *Dfetch* uses CycloneDX JSON format
      in two contexts: (1) ``dfetch report -t sbom`` generates an SBOM of a
      project's vendored dependencies, listing each dependency's URL, revision,
      auto-detected licence, and — for :term:`Archive` sources — the
      cryptographic hash from the :term:`Integrity` field; (2) the dfetch
      release pipeline generates a CycloneDX SBOM *about dfetch itself* as a
      Sigstore-signed :term:`Attestation` on every release, verifiable with
      ``gh attestation verify`` (see :ref:`verify-integrity`).

   Source
      The subfolder inside an upstream repository to copy, declared with the
      ``src:`` attribute.  Only the files under that path are placed in the
      :term:`Destination`; the rest of the upstream repository is ignored.
      License files are always retained regardless of the ``src:`` setting.

   Sub-manifest
      A ``dfetch.yaml`` found inside a fetched :term:`Subproject`.  After
      fetching, *Dfetch* inspects sub-manifests and reports any further
      dependencies they declare, so you can decide whether to vendor those
      transitively.  Pass ``--no-recommendations`` to ``dfetch update`` to
      skip this check.

   Subproject
      A dependency declared in the :term:`Manifest` that *Dfetch* copies into
      the :term:`Superproject`.  A subproject can be sourced from a Git
      repository, an SVN repository, or a plain :term:`Archive` URL.

   Superproject
      The top-level project that owns the :term:`Manifest`.  It coordinates
      all :term:`Subproject` dependencies and is typically the repository that
      is committed to version control.

   Attestation
      A cryptographic claim about a software artifact, signed by GitHub Actions
      via :term:`Sigstore` and published in the `dfetch attestation registry
      <https://github.com/dfetch-org/dfetch/attestations>`_.  Attestations are
      verifiable by anyone using ``gh attestation verify`` without trusting any
      private key.  dfetch publishes four attestation types on every release:
      :term:`Build Provenance`, :term:`SBOM` (CycloneDX composition of the
      package), :term:`VSA`, and in-toto Test Results (the CI test suite passed
      before any binary was produced).  :term:`Source Provenance` is published
      on every push to ``main`` rather than per-release.  See
      :ref:`verify-integrity` for per-artifact verification instructions.

   Build Provenance
      An :term:`SLSA` attestation recording the exact source commit and GitHub
      Actions workflow that produced a release artifact.  Lets consumers verify
      that a binary was built from the claimed source by the official CI workflow
      and was not injected or modified after the build.  Required by supply-chain
      control C-037; verifiable with ``gh attestation verify`` (see
      :ref:`verify-integrity`).

   CRA
      Cyber Resilience Act — Regulation (EU) 2024/2847, in force from
      10 December 2024.  It imposes cybersecurity requirements on manufacturers
      of *Products with Digital Elements* placed on the EU market.  dfetch's
      :ref:`security model <security>` aligns with the 13 CRA Annex I essential
      requirements (ECR-a through ECR-m) using the :term:`EN 40000` harmonised
      standards and :term:`OSCAL` machine-readable documentation.

   EN 40000
      The CEN/CENELEC family of harmonised cybersecurity standards developed
      under the :term:`CRA` by CEN/CLC/JTC 13.  The relevant parts for dfetch
      are prEN 40000-1-2 (product security context), prEN 40000-1-3
      (vulnerability handling), and prEN 40000-1-4 (security objectives SO.*
      that bridge CRA essential requirements to concrete controls).  Once
      published in the OJEU, compliance with these standards gives a presumption
      of conformity with the corresponding CRA requirements.  dfetch's mapping
      is captured in :doc:`/explanation/compliance_track`.

   OSCAL
      Open Security Controls Assessment Language — a set of NIST-published
      JSON/XML schemas for machine-readable security control documentation.
      dfetch uses OSCAL 1.1.2 for
      ``security/cra_pren_4000014_oscal_catalog.json`` (the prEN 40000-1-4
      catalog) and ``security/dfetch.component-definition.json`` (dfetch's
      Component Definition, which maps the 46 dfetch controls to :term:`CRA`
      ECRs via :term:`EN 40000` Security Objectives).

   SARIF
      Static Analysis Results Interchange Format — an OASIS standard
      (version 2.1.0) for exchanging static-analysis findings.
      ``dfetch check --output-type sarif`` produces a SARIF file that can be
      uploaded to GitHub code scanning to surface out-of-date or missing
      dependencies as security alerts in pull requests.  See
      :ref:`check-ci-github`.

   Sigstore
      An open-source project providing transparency-log-backed code-signing
      without long-lived private keys.  GitHub Actions signs dfetch's
      :term:`Attestation` artifacts via Sigstore; the signatures are anchored
      in a public, append-only transparency log (Rekor) so that forgery is
      detectable by anyone.

   SLSA
      Supply-chain Levels for Software Artifacts — a security framework defining
      increasing levels of supply-chain integrity guarantees.  dfetch publishes
      two SLSA attestation types per release: :term:`Build Provenance`
      (source-to-binary traceability) and :term:`Source Provenance` (governance
      controls on the ``main`` branch).

   Source Provenance
      An :term:`SLSA` attestation recording which branch-protection, code-review,
      and ancestry-enforcement controls were active when a commit was merged to
      ``main``.  Lets consumers verify that dfetch source code went through the
      required governance process before being included in a release.  Required
      by control C-037; published on every push to ``main`` via
      ``slsa-framework/source-actions``.  See :ref:`verify-integrity`.

   STRIDE
      A threat-classification framework developed by Microsoft: Spoofing,
      Tampering, Repudiation, Information Disclosure, Denial of Service,
      Elevation of Privilege.  Every threat in ``security/threats.json`` is
      classified by STRIDE category to identify which security property it
      violates and which controls address it.  See
      :doc:`/explanation/threat_model_supply_chain` and
      :doc:`/explanation/threat_model_usage`.

   Vendoring
      The practice of copying third-party source code directly into your own
      repository rather than relying on a package manager to fetch it at build
      time.  *Dfetch* automates the fetch, version-pinning, patching, and
      update lifecycle of vendored dependencies.  See :ref:`Vendoring <vendoring>`
      for a detailed discussion of the trade-offs.

   VSA
      Verification Summary Attestation — an :term:`SLSA` attestation attached
      to binary installer artifacts that records the source archive was itself
      attested and verified before the binary was produced.  It links
      source-level trust to the installed binary so consumers can confirm the
      full source-to-installer chain without re-verifying the source separately.
      See :ref:`verify-integrity`.
