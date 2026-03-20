Feature: Create a CycloneDX SBOM for archive dependencies

    *Dfetch* can generate a software Bill-of-Materials (SBOM) that includes
    dependencies fetched from tar/zip archives.

    For archive components the SBOM records:
    - A ``generic`` Package URL (PURL) with a ``download_url`` qualifier
      pointing at the archive.
    - An external reference of type ``distribution`` (not ``vcs``).
    - A ``SHA-256`` component hash when a ``hash:`` field is present in the
      manifest, so downstream tooling can verify supply-chain integrity.

    Scenario: A fetched archive without a hash generates a json sbom
        Given an archive "SomeProject.tar.gz"
        And the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              projects:
                - name: SomeProject
                  url: some-remote-server/SomeProject.tar.gz
                  vcs: archive
            """
        And all projects are updated
        When I run "dfetch report -t sbom"
        Then the 'report.json' json file includes
            """
            {
                "components": [
                    {
                        "name": "SomeProject",
                        "type": "library",
                        "externalReferences": [
                            {
                                "type": "distribution",
                                "url": "<archive-url>"
                            }
                        ]
                    }
                ]
            }
            """

    Scenario: A fetched archive with sha256 hash generates a json sbom with hash
        Given an archive "SomeProject.tar.gz"
        And the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              projects:
                - name: SomeProject
                  url: some-remote-server/SomeProject.tar.gz
                  vcs: archive
                  hash: sha256:<archive-sha256>
            """
        And all projects are updated
        When I run "dfetch report -t sbom"
        Then the 'report.json' json file includes
            """
            {
                "components": [
                    {
                        "name": "SomeProject",
                        "version": "sha256:<archive-sha256>",
                        "type": "library",
                        "hashes": [
                            {
                                "alg": "SHA-256",
                                "content": "<archive-sha256>"
                            }
                        ],
                        "externalReferences": [
                            {
                                "type": "distribution",
                                "url": "<archive-url>"
                            }
                        ]
                    }
                ]
            }
            """

    Scenario: An unfetched archive with hash in manifest reports hash as version
        Given an archive "SomeProject.tar.gz"
        And the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              projects:
                - name: SomeProject
                  url: some-remote-server/SomeProject.tar.gz
                  vcs: archive
                  hash: sha256:<archive-sha256>
            """
        When I run "dfetch report -t sbom"
        Then the 'report.json' json file includes
            """
            {
                "components": [
                    {
                        "name": "SomeProject",
                        "version": "sha256:<archive-sha256>",
                        "type": "library",
                        "hashes": [
                            {
                                "alg": "SHA-256",
                                "content": "<archive-sha256>"
                            }
                        ]
                    }
                ]
            }
            """
