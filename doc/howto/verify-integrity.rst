
.. _verify-integrity:

Verify release integrity
========================

Installing software means trusting that the binary matches the published source,
was built by the official CI workflow, and that tests passed before the artifact
was produced.  dfetch publishes cryptographic attestations signed by GitHub
Actions and anchored in `Sigstore <https://www.sigstore.dev/>`_ so you can
check each of those claims yourself.  All attestations are published in the
`attestation registry <https://github.com/dfetch-org/dfetch/attestations>`_.

There are five kinds of attestation, in pipeline order from source to artifact:

- **source provenance attestation** (SLSA Source Track): records that branch
  protection, mandatory code review, and ancestry enforcement were in place when
  the commit was merged to ``main``.
- **Test Result Attestation** (in-toto): records that the full CI test suite ran
  against this exact source archive and every check passed, before any binary
  was produced.
- **Build Provenance**: records that the artifact was produced from the official
  source commit by the official CI workflow, including the exact inputs used at
  build time.
- **SBOM Attestation** (CycloneDX): lists every dependency bundled in the
  package so you can audit its composition.
- **Verification Summary Attestation (VSA)**: records that the source archive
  was itself attested and verified before the binary was produced.

The attestations available depend on the artifact:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Artifact
     - Attestations
   * - Binary installer (``.deb`` / ``.pkg`` / ``.msi``)
     - Build Provenance, SBOM Attestation, Verification Summary Attestation
       (VSA) (requires source provenance verification to pass)
   * - PyPI wheel
     - SBOM Attestation only
   * - Source archive (``dfetch-source.tar.gz``)
     - Build Provenance, Test Result Attestation
   * - Every commit merged to ``main``
     - source provenance attestation (SLSA Source Track)

To verify, use the `GitHub CLI <https://cli.github.com/>`_ (version 2.49 or later
— attestation verification was introduced in that release). Pass
``--predicate-type`` to target one kind specifically; omit it to accept any.

In the commands below, replace ``@refs/tags/v<version>`` with
``@refs/heads/main`` when verifying a development build installed directly
from the ``main`` branch.

.. note::

   Always supply both ``--cert-identity`` **and**
   ``--cert-oidc-issuer https://token.actions.githubusercontent.com``.
   Without the issuer flag, a certificate for the same workflow path could be
   issued by a different OIDC provider (for example a self-hosted Sigstore
   instance).  Both flags together pin verification to GitHub Actions as the
   identity provider.

.. tabs::

    .. tab:: Linux

        **Binary installer: Build Provenance**

        .. code-block:: bash

            $ gh attestation verify dfetch-<version>-nix.deb \
                --repo dfetch-org/dfetch \
                --predicate-type https://slsa.dev/provenance/v1 \
                --cert-identity https://github.com/dfetch-org/dfetch/.github/workflows/build.yml@refs/tags/v<version> \
                --cert-oidc-issuer https://token.actions.githubusercontent.com

        **Binary installer: SBOM Attestation**

        .. code-block:: bash

            $ gh attestation verify dfetch-<version>-nix.deb \
                --repo dfetch-org/dfetch \
                --predicate-type https://cyclonedx.org/bom \
                --cert-identity https://github.com/dfetch-org/dfetch/.github/workflows/build.yml@refs/tags/v<version> \
                --cert-oidc-issuer https://token.actions.githubusercontent.com

        **Binary installer: Verification Summary Attestation (VSA)**

        .. code-block:: bash

            $ gh attestation verify dfetch-<version>-nix.deb \
                --repo dfetch-org/dfetch \
                --predicate-type https://slsa.dev/verification_summary/v1 \
                --cert-identity https://github.com/dfetch-org/dfetch/.github/workflows/build.yml@refs/tags/v<version> \
                --cert-oidc-issuer https://token.actions.githubusercontent.com

        **pip / PyPI wheel: SBOM Attestation**

        Download the wheel before installing so you have the original file to verify:

        .. code-block:: bash

            $ pip download dfetch==<version> --no-deps -d .
            $ gh attestation verify dfetch-<version>-py3-none-any.whl \
                --repo dfetch-org/dfetch \
                --predicate-type https://cyclonedx.org/bom \
                --cert-identity https://github.com/dfetch-org/dfetch/.github/workflows/python-publish.yml@refs/tags/v<version> \
                --cert-oidc-issuer https://token.actions.githubusercontent.com

    .. tab:: macOS

        **Binary installer: Build Provenance**

        .. code-block:: bash

            $ gh attestation verify dfetch-<version>-osx.pkg \
                --repo dfetch-org/dfetch \
                --predicate-type https://slsa.dev/provenance/v1 \
                --cert-identity https://github.com/dfetch-org/dfetch/.github/workflows/build.yml@refs/tags/v<version> \
                --cert-oidc-issuer https://token.actions.githubusercontent.com

        **Binary installer: SBOM Attestation**

        .. code-block:: bash

            $ gh attestation verify dfetch-<version>-osx.pkg \
                --repo dfetch-org/dfetch \
                --predicate-type https://cyclonedx.org/bom \
                --cert-identity https://github.com/dfetch-org/dfetch/.github/workflows/build.yml@refs/tags/v<version> \
                --cert-oidc-issuer https://token.actions.githubusercontent.com

        **Binary installer: Verification Summary Attestation (VSA)**

        .. code-block:: bash

            $ gh attestation verify dfetch-<version>-osx.pkg \
                --repo dfetch-org/dfetch \
                --predicate-type https://slsa.dev/verification_summary/v1 \
                --cert-identity https://github.com/dfetch-org/dfetch/.github/workflows/build.yml@refs/tags/v<version> \
                --cert-oidc-issuer https://token.actions.githubusercontent.com

        **pip / PyPI wheel: SBOM Attestation**

        Download the wheel before installing so you have the original file to verify:

        .. code-block:: bash

            $ pip download dfetch==<version> --no-deps -d .
            $ gh attestation verify dfetch-<version>-py3-none-any.whl \
                --repo dfetch-org/dfetch \
                --predicate-type https://cyclonedx.org/bom \
                --cert-identity https://github.com/dfetch-org/dfetch/.github/workflows/python-publish.yml@refs/tags/v<version> \
                --cert-oidc-issuer https://token.actions.githubusercontent.com

    .. tab:: Windows

        **Binary installer: Build Provenance**

        .. code-block:: powershell

            > gh attestation verify dfetch-<version>-win.msi `
                --repo dfetch-org/dfetch `
                --predicate-type https://slsa.dev/provenance/v1 `
                --cert-identity https://github.com/dfetch-org/dfetch/.github/workflows/build.yml@refs/tags/v<version> `
                --cert-oidc-issuer https://token.actions.githubusercontent.com

        **Binary installer: SBOM Attestation**

        .. code-block:: powershell

            > gh attestation verify dfetch-<version>-win.msi `
                --repo dfetch-org/dfetch `
                --predicate-type https://cyclonedx.org/bom `
                --cert-identity https://github.com/dfetch-org/dfetch/.github/workflows/build.yml@refs/tags/v<version> `
                --cert-oidc-issuer https://token.actions.githubusercontent.com

        **Binary installer: Verification Summary Attestation (VSA)**

        .. code-block:: powershell

            > gh attestation verify dfetch-<version>-win.msi `
                --repo dfetch-org/dfetch `
                --predicate-type https://slsa.dev/verification_summary/v1 `
                --cert-identity https://github.com/dfetch-org/dfetch/.github/workflows/build.yml@refs/tags/v<version> `
                --cert-oidc-issuer https://token.actions.githubusercontent.com

        **pip / PyPI wheel: SBOM Attestation**

        Download the wheel before installing so you have the original file to verify:

        .. code-block:: powershell

            > pip download dfetch==<version> --no-deps -d .
            > gh attestation verify dfetch-<version>-py3-none-any.whl `
                --repo dfetch-org/dfetch `
                --predicate-type https://cyclonedx.org/bom `
                --cert-identity https://github.com/dfetch-org/dfetch/.github/workflows/python-publish.yml@refs/tags/v<version> `
                --cert-oidc-issuer https://token.actions.githubusercontent.com

Source archive: Build Provenance and Test Result Attestation
------------------------------------------------------------

The source archive has two attestations and is produced for every release and
every ``main``-branch commit. Download ``dfetch-source.tar.gz`` from the *Artifacts*
section of the relevant CI run, then verify each in turn. Use
``@refs/tags/v<version>`` for a release or ``@refs/heads/main`` for a
development build.

.. note::

   The commands below use a backslash for line continuation (Linux and macOS).
   On Windows PowerShell, replace each backslash with a backtick.

Verify Build Provenance:

.. code-block:: bash

    $ gh attestation verify dfetch-source.tar.gz \
        --repo dfetch-org/dfetch \
        --predicate-type https://slsa.dev/provenance/v1 \
        --cert-identity https://github.com/dfetch-org/dfetch/.github/workflows/source-provenance.yml@refs/tags/v<version> \
        --cert-oidc-issuer https://token.actions.githubusercontent.com

Verify Test Result Attestation:

.. code-block:: bash

    $ gh attestation verify dfetch-source.tar.gz \
        --repo dfetch-org/dfetch \
        --predicate-type https://in-toto.io/attestation/test-result/v0.1 \
        --cert-identity https://github.com/dfetch-org/dfetch/.github/workflows/test.yml@refs/tags/v<version> \
        --cert-oidc-issuer https://token.actions.githubusercontent.com

Source governance: source provenance attestation (SLSA Source Track)
---------------------------------------------------------------------

Every commit merged to ``main`` has a source provenance attestation proving that
branch protection, mandatory code review, and ancestry enforcement were in place
when the commit landed.  These attestations are published by
``slsa-framework/source-actions/slsa_with_provenance`` and stored in the
`attestation registry <https://github.com/dfetch-org/dfetch/attestations>`_.
Replace ``<sha>`` with the 40-character commit SHA you want to verify.

.. note::

   The commands below use a backslash for line continuation (Linux and macOS).
   On Windows PowerShell, replace each backslash with a backtick.

.. code-block:: bash

    $ gh attestation verify \
        "git+https://github.com/dfetch-org/dfetch@<sha>" \
        --repo dfetch-org/dfetch \
        --predicate-type https://slsa.dev/source_provenance/v1 \
        --cert-identity https://github.com/dfetch-org/dfetch/.github/workflows/source-provenance.yml@refs/heads/main \
        --cert-oidc-issuer https://token.actions.githubusercontent.com

See `GitHub artifact attestations`_ for details.

.. note::

   The VSA is present on releases built from a commit whose source provenance
   was verified.  If the ``verification_summary`` attestation is absent for a
   release, fall back to checking Build Provenance and SBOM Attestation
   independently.

.. _`GitHub artifact attestations`: https://docs.github.com/en/actions/security-for-github-actions/using-artifact-attestations
