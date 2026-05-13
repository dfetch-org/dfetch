Verify release integrity
========================

Every dfetch release, and every commit merged to ``main``, has cryptographic
attestations signed by GitHub Actions and anchored in
`Sigstore <https://www.sigstore.dev/>`_, all published in the
`attestation registry <https://github.com/dfetch-org/dfetch/attestations>`_.
There are four complementary kinds:

- **SLSA build provenance** — answers *"where did this come from?"*: proves the
  artifact was produced from the official source commit by the official CI
  workflow, and records the exact inputs used at build time.
- **SBOM attestation** (CycloneDX) — answers *"what is inside it?"*: lists every
  dependency bundled in the package so you can audit its composition.
- **Verification Summary Attestation (VSA)** — answers *"was the source
  independently verified?"*: records that the source archive for this commit was
  attested and verified before the binary was produced, linking source-level
  trust to the binary package.
- **Test result attestation** (in-toto) — answers *"did the source pass its tests?"*:
  records that the full CI test suite ran against this exact source archive and every
  check passed, before any binary was produced.

Binary installers have **build provenance, SBOM, and VSA** attestations when source
provenance verification passes (signed by ``build.yml``).
Python packages installed from PyPI have an **SBOM attestation only** (signed by
``python-publish.yml``).
The source archive has a **SLSA build provenance** attestation (signed by
``source-provenance.yml``) and a **test result attestation** (signed by ``test.yml``).

To verify, use the `GitHub CLI <https://cli.github.com/>`_. Pass
``--predicate-type`` to target one kind specifically; omit it to accept any.

In the commands below, replace ``@refs/tags/v<version>`` with
``@refs/heads/main`` when verifying a development build installed directly
from the ``main`` branch.

.. tabs::

    .. tab:: Linux

        **Binary installer — verify build provenance:**

        .. code-block:: bash

            $ gh attestation verify dfetch-<version>-nix.deb \
                --repo dfetch-org/dfetch \
                --predicate-type https://slsa.dev/provenance/v1 \
                --cert-identity https://github.com/dfetch-org/dfetch/.github/workflows/build.yml@refs/tags/v<version> \
                --cert-oidc-issuer https://token.actions.githubusercontent.com

        **Binary installer — verify SBOM attestation:**

        .. code-block:: bash

            $ gh attestation verify dfetch-<version>-nix.deb \
                --repo dfetch-org/dfetch \
                --predicate-type https://cyclonedx.org/bom \
                --cert-identity https://github.com/dfetch-org/dfetch/.github/workflows/build.yml@refs/tags/v<version> \
                --cert-oidc-issuer https://token.actions.githubusercontent.com

        **Binary installer — verify source provenance summary (VSA):**

        .. code-block:: bash

            $ gh attestation verify dfetch-<version>-nix.deb \
                --repo dfetch-org/dfetch \
                --predicate-type https://slsa.dev/verification_summary/v1 \
                --cert-identity https://github.com/dfetch-org/dfetch/.github/workflows/build.yml@refs/tags/v<version> \
                --cert-oidc-issuer https://token.actions.githubusercontent.com

        **pip / PyPI wheel — verify SBOM attestation:**

        Download the wheel before installing so you have the original file to verify:

        .. code-block:: bash

            $ pip download dfetch==<version> --no-deps -d .
            $ gh attestation verify dfetch-<version>-py3-none-any.whl \
                --repo dfetch-org/dfetch \
                --predicate-type https://cyclonedx.org/bom \
                --cert-identity https://github.com/dfetch-org/dfetch/.github/workflows/python-publish.yml@refs/tags/v<version> \
                --cert-oidc-issuer https://token.actions.githubusercontent.com

    .. tab:: macOS

        **Binary installer — verify build provenance:**

        .. code-block:: bash

            $ gh attestation verify dfetch-<version>-osx.pkg \
                --repo dfetch-org/dfetch \
                --predicate-type https://slsa.dev/provenance/v1 \
                --cert-identity https://github.com/dfetch-org/dfetch/.github/workflows/build.yml@refs/tags/v<version> \
                --cert-oidc-issuer https://token.actions.githubusercontent.com

        **Binary installer — verify SBOM attestation:**

        .. code-block:: bash

            $ gh attestation verify dfetch-<version>-osx.pkg \
                --repo dfetch-org/dfetch \
                --predicate-type https://cyclonedx.org/bom \
                --cert-identity https://github.com/dfetch-org/dfetch/.github/workflows/build.yml@refs/tags/v<version> \
                --cert-oidc-issuer https://token.actions.githubusercontent.com

        **Binary installer — verify source provenance summary (VSA):**

        .. code-block:: bash

            $ gh attestation verify dfetch-<version>-osx.pkg \
                --repo dfetch-org/dfetch \
                --predicate-type https://slsa.dev/verification_summary/v1 \
                --cert-identity https://github.com/dfetch-org/dfetch/.github/workflows/build.yml@refs/tags/v<version> \
                --cert-oidc-issuer https://token.actions.githubusercontent.com

        **pip / PyPI wheel — verify SBOM attestation:**

        Download the wheel before installing so you have the original file to verify:

        .. code-block:: bash

            $ pip download dfetch==<version> --no-deps -d .
            $ gh attestation verify dfetch-<version>-py3-none-any.whl \
                --repo dfetch-org/dfetch \
                --predicate-type https://cyclonedx.org/bom \
                --cert-identity https://github.com/dfetch-org/dfetch/.github/workflows/python-publish.yml@refs/tags/v<version> \
                --cert-oidc-issuer https://token.actions.githubusercontent.com

    .. tab:: Windows

        **Binary installer — verify build provenance:**

        .. code-block:: powershell

            > gh attestation verify dfetch-<version>-win.msi `
                --repo dfetch-org/dfetch `
                --predicate-type https://slsa.dev/provenance/v1 `
                --cert-identity https://github.com/dfetch-org/dfetch/.github/workflows/build.yml@refs/tags/v<version> `
                --cert-oidc-issuer https://token.actions.githubusercontent.com

        **Binary installer — verify SBOM attestation:**

        .. code-block:: powershell

            > gh attestation verify dfetch-<version>-win.msi `
                --repo dfetch-org/dfetch `
                --predicate-type https://cyclonedx.org/bom `
                --cert-identity https://github.com/dfetch-org/dfetch/.github/workflows/build.yml@refs/tags/v<version> `
                --cert-oidc-issuer https://token.actions.githubusercontent.com

        **Binary installer — verify source provenance summary (VSA):**

        .. code-block:: powershell

            > gh attestation verify dfetch-<version>-win.msi `
                --repo dfetch-org/dfetch `
                --predicate-type https://slsa.dev/verification_summary/v1 `
                --cert-identity https://github.com/dfetch-org/dfetch/.github/workflows/build.yml@refs/tags/v<version> `
                --cert-oidc-issuer https://token.actions.githubusercontent.com

        **pip / PyPI wheel — verify SBOM attestation:**

        Download the wheel before installing so you have the original file to verify:

        .. code-block:: powershell

            > pip download dfetch==<version> --no-deps -d .
            > gh attestation verify dfetch-<version>-py3-none-any.whl `
                --repo dfetch-org/dfetch `
                --predicate-type https://cyclonedx.org/bom `
                --cert-identity https://github.com/dfetch-org/dfetch/.github/workflows/python-publish.yml@refs/tags/v<version> `
                --cert-oidc-issuer https://token.actions.githubusercontent.com

**Source archive — verify build provenance and test results:**

The source archive has two attestations and is produced for every release and
every ``main``-branch commit. Download ``dfetch-source.tar.gz`` from the *Artifacts*
section of the relevant CI run, then verify each in turn. Use
``@refs/tags/v<version>`` for a release or ``@refs/heads/main`` for a
development build.

Verify SLSA build provenance (proves the archive was produced by the official
workflow from the tagged commit):

.. code-block:: bash

    $ gh attestation verify dfetch-source.tar.gz \
        --repo dfetch-org/dfetch \
        --predicate-type https://slsa.dev/provenance/v1 \
        --cert-identity https://github.com/dfetch-org/dfetch/.github/workflows/source-provenance.yml@refs/tags/v<version> \
        --cert-oidc-issuer https://token.actions.githubusercontent.com

Verify test results (proves the full CI suite passed on that exact source before
any binary was produced):

.. code-block:: bash

    $ gh attestation verify dfetch-source.tar.gz \
        --repo dfetch-org/dfetch \
        --predicate-type https://in-toto.io/attestation/test-result/v0.1 \
        --cert-identity https://github.com/dfetch-org/dfetch/.github/workflows/test.yml@refs/tags/v<version> \
        --cert-oidc-issuer https://token.actions.githubusercontent.com

See `GitHub artifact attestations`_ for details.

.. note::

   The VSA is present on releases built from a commit whose source provenance
   was verified.  If the ``verification_summary`` attestation is absent for a
   release, fall back to checking build provenance and SBOM independently.

.. note::

   ``--cert-oidc-issuer https://token.actions.githubusercontent.com`` pins
   verification to GitHub Actions as the identity provider.  Without it, an
   attacker could generate a valid attestation using a different OIDC issuer
   (for example a self-hosted Sigstore instance) that also produces a
   certificate matching the ``--cert-identity`` workflow path.  Supplying
   both flags together ensures the certificate was issued specifically by
   GitHub Actions for the declared workflow.

.. _`GitHub artifact attestations`: https://docs.github.com/en/actions/security-for-github-actions/using-artifact-attestations
