Installation
============

From pip
--------

If you are using python you can install the latest release with:

.. code-block:: bash

   $ pip install dfetch

Or install the latest version from the main branch:

.. code-block:: bash

   $ pip install git+https://github.com/dfetch-org/dfetch.git@main#egg=dfetch

Binary distributions
--------------------

Each release on the `releases page <https://github.com/dfetch-org/dfetch/releases>`_
provides pre-built installers for all major platforms, so no compilation is required.

Each installer package has a name in the format ``<version>-<platform>``.

- ``<version>`` shows the software version:

    - If it includes ``dev``, it is a development release (for testing).
    - If it is only numbers (e.g. ``0.13.0``), it is an official release.

- ``<platform>`` indicates the system the installer is for: ``nix`` (Linux), ``osx`` (Mac), or ``win`` (Windows).

The version is automatically determined from the project and used to name the installer files.

.. tabs::

    .. tab:: Linux

        Download the  ``.deb`` or ``.rpm`` package from the releases page and install it.

        Debian / Ubuntu (``.deb``):

        .. code-block:: bash

            $ sudo dpkg -i dfetch-<version>-nix.deb

        RPM-based distributions (``.rpm``):

        .. code-block:: bash

            $ sudo dnf install dfetch-<version>-nix.rpm
            # or
            $ sudo rpm -i dfetch-<version>-nix.rpm

    .. tab:: macOS

        Download the ``.pkg`` package from the releases page and install it.

        .. code-block:: bash

            $ sudo installer -pkg dfetch-<version>-osx.pkg -target /

    .. tab:: Windows

        Install dfetch directly through winget:

        .. code-block:: powershell

            > winget install -e --id DFetch-org.DFetch

        Or download the ``.msi`` installer from the releases page and install by double-clicking or use:

        .. code-block:: powershell

            > msiexec /i dfetch-<version>-win.msi

        Uninstalling can be done through the regular Add/Remove programs section.

Validating Installation
-----------------------

Run the following command to verify the installation

.. code-block:: bash

   $ dfetch environment

.. asciinema:: ../asciicasts/environment.cast

Verifying release integrity
---------------------------

Every dfetch release has cryptographic attestations signed by GitHub Actions
and anchored in `Sigstore <https://www.sigstore.dev/>`_, all published in the
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
The source archive has a **test result attestation** (signed by ``test.yml``).

To verify, use the `GitHub CLI <https://cli.github.com/>`_. Pass
``--predicate-type`` to target one kind specifically; omit it to accept either.

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

        .. code-block:: bash

            $ gh attestation verify ~/.local/lib/python3.x/site-packages/dfetch-<version>.dist-info/ \
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

        .. code-block:: bash

            $ gh attestation verify /usr/local/lib/python3.x/site-packages/dfetch-<version>.dist-info/ \
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

        .. code-block:: powershell

            > gh attestation verify $env:APPDATA\Python\Python3x\site-packages\dfetch-<version>.dist-info\ `
                --repo dfetch-org/dfetch `
                --predicate-type https://cyclonedx.org/bom `
                --cert-identity https://github.com/dfetch-org/dfetch/.github/workflows/python-publish.yml@refs/tags/v<version> `
                --cert-oidc-issuer https://token.actions.githubusercontent.com

**Source archive — verify test results:**

The test result attestation proves the full CI suite passed on that exact source
before any binary was produced.
To verify locally, download ``source.tar.gz`` from the *Artifacts* section of the
release CI run, then run:

.. code-block:: bash

    $ gh attestation verify source.tar.gz \
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
