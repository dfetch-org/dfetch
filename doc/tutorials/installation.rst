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

Every dfetch release carries cryptographic attestations signed by GitHub Actions
and anchored in `Sigstore <https://www.sigstore.dev/>`_. There are two
complementary kinds:

- **SLSA build provenance** — answers *"where did this come from?"*: proves the
  artifact was produced from the official source commit by the official CI
  workflow, and records the exact inputs used at build time.
- **SBOM attestation** (CycloneDX) — answers *"what is inside it?"*: lists every
  dependency bundled in the package so you can audit its composition.

Binary installers carry **both** kinds of attestation (signed by ``build.yml``).
Python packages installed from PyPI carry an **SBOM attestation only** (signed by
``python-publish.yml``).

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

        **pip / PyPI wheel — verify SBOM attestation:**

        .. code-block:: powershell

            > gh attestation verify $env:APPDATA\Python\Python3x\site-packages\dfetch-<version>.dist-info\ `
                --repo dfetch-org/dfetch `
                --predicate-type https://cyclonedx.org/bom `
                --cert-identity https://github.com/dfetch-org/dfetch/.github/workflows/python-publish.yml@refs/tags/v<version> `
                --cert-oidc-issuer https://token.actions.githubusercontent.com

See `GitHub artifact attestations`_ for details.

.. note::

   ``--cert-oidc-issuer https://token.actions.githubusercontent.com`` pins
   verification to GitHub Actions as the identity provider.  Without it, an
   attacker could generate a valid attestation using a different OIDC issuer
   (for example a self-hosted Sigstore instance) that also produces a
   certificate matching the ``--cert-identity`` workflow path.  Supplying
   both flags together ensures the certificate was issued specifically by
   GitHub Actions for the declared workflow.

.. _`GitHub artifact attestations`: https://docs.github.com/en/actions/security-for-github-actions/using-artifact-attestations
