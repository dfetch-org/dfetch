
.. _sbom:

Generate an SBOM
================

``dfetch report`` generates a `CycloneDX`_ SBOM listing every vendored
dependency with its URL, revision, and auto-detected license.  Downstream
tools can use the SBOM to monitor for known vulnerabilities or enforce a
license policy across an organisation.

.. asciinema:: ../asciicasts/sbom.cast

.. code-block:: sh

    $ dfetch report -t sbom -o dfetch.cdx.json

*Dfetch* parses each project's license at report time, it can recognise common
license files and detect the license type with high accuracy. If a project doesn't
include a license file or has an unknown license, *Dfetch* keeps the license field
empty in the SBOM.

Archive dependencies (``tar.gz``, ``zip``, …) are recorded with a
``distribution`` external reference.  When an ``integrity.hash:`` field is set
in the manifest the SBOM includes a ``SHA-256`` component hash for
supply-chain integrity verification.

.. scenario-include:: ../features/report-sbom.feature
   :scenario: A fetched project generates a json sbom

.. scenario-include:: ../features/report-sbom-archive.feature
   :scenario: A fetched archive without a hash generates a json sbom

.. scenario-include:: ../features/report-sbom-archive.feature
   :scenario: A fetched archive with sha256 hash generates a json sbom with hash

GitLab
------

Upload the SBOM as a CycloneDX artifact so GitLab surfaces it in the
dependency scanning dashboard.  See `GitLab dependency scanning`_ for details.

.. code-block:: yaml

    dfetch:
      image: "python:3.13"
      script:
        - pip install dfetch
        - dfetch report -t sbom -o dfetch.cdx.json
      artifacts:
        reports:
          cyclonedx:
            - dfetch.cdx.json

GitHub Actions
--------------

Generate and upload the SBOM as a workflow artifact.  See `GitHub dependency
submission`_ for details.

.. code-block:: yaml

    jobs:
      SBOM-generation:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v5
          - uses: actions/setup-python@v6
            with:
              python-version: '3.13'
          - name: Generate SBOM
            run: pip install dfetch && dfetch report -t sbom -o dfetch.cdx.json
          - uses: actions/upload-artifact@v4
            with:
              name: sbom
              path: dfetch.cdx.json

.. _`CycloneDX`: https://cyclonedx.org/use-cases/
.. _`GitLab dependency scanning`: https://docs.gitlab.com/user/application_security/dependency_scanning/dependency_scanning_sbom/#cyclonedx-software-bill-of-materials
.. _`GitHub dependency submission`: https://docs.github.com/en/code-security/supply-chain-security/understanding-your-software-supply-chain/using-the-dependency-submission-api
