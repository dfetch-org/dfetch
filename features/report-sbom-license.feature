Feature: SBOM license transparency

    When *dfetch* scans a fetched component for license information it records
    the outcome in the CycloneDX ``licenses`` field.

    Two positive outcomes trigger inclusion of the full license text:

    * A license-like file (``LICENSE``, ``COPYING``, …) was found and
      successfully classified → the SPDX identifier **and** the raw license
      text (base64-encoded) are embedded so downstream tooling can verify the
      text matches the declared identifier.

    Two failure cases trigger NOASSERTION instead:

    * A license-like file was found but could not be matched to a known SPDX
      identifier with sufficient confidence.
    * No license-like file was present in the fetched source tree at all.

    Scenario: A fetched archive with an identified license embeds base64 license text
        Given an archive "SomeProject.tar.gz" with a "MIT" license
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
                        "licenses": [
                            {
                                "license": {
                                    "id": "MIT",
                                    "text": {
                                        "contentType": "text/plain",
                                        "encoding": "base64",
                                        "content": "<license-base64>"
                                    }
                                }
                            }
                        ],
                        "evidence": {
                            "licenses": [
                                {
                                    "license": {
                                        "id": "MIT",
                                        "text": {
                                            "contentType": "text/plain",
                                            "encoding": "base64",
                                            "content": "<license-base64>"
                                        }
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
            """

    Scenario: A fetched archive with an unclassifiable license file gets NOASSERTION
        Given an archive "SomeProject.tar.gz" with the files
            | path    |
            | LICENSE |
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
                        "licenses": [
                            {
                                "license": {
                                    "id": "NOASSERTION",
                                    "acknowledgement": "concluded",
                                    "text": {
                                        "content": "License file(s) found (LICENSE) but could not be classified",
                                        "contentType": "text/plain"
                                    }
                                }
                            }
                        ],
                        "properties": [
                            {
                                "name": "dfetch:license:finding",
                                "value": "License file(s) found (LICENSE) but could not be classified"
                            },
                            {
                                "name": "dfetch:license:noassertion:reason",
                                "value": "UNCLASSIFIABLE_LICENSE_TEXT"
                            },
                            {
                                "name": "dfetch:license:threshold",
                                "value": "0.80"
                            },
                            {
                                "name": "dfetch:license:tool",
                                "value": "<infer-license-version>"
                            }
                        ],
                        "evidence": {
                            "licenses": [
                                {
                                    "license": {
                                        "id": "NOASSERTION",
                                        "acknowledgement": "concluded",
                                        "text": {
                                            "content": "License file(s) found (LICENSE) but could not be classified",
                                            "contentType": "text/plain"
                                        }
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
            """

    Scenario: A fetched archive with no license file gets NOASSERTION
        Given an archive "SomeProject.tar.gz" with the files
            | path       |
            | README.md  |
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
                        "licenses": [
                            {
                                "license": {
                                    "id": "NOASSERTION",
                                    "acknowledgement": "concluded",
                                    "text": {
                                        "content": "No license file found in source tree",
                                        "contentType": "text/plain"
                                    }
                                }
                            }
                        ],
                        "properties": [
                            {
                                "name": "dfetch:license:finding",
                                "value": "No license file found in source tree"
                            },
                            {
                                "name": "dfetch:license:noassertion:reason",
                                "value": "NO_LICENSE_FILE"
                            },
                            {
                                "name": "dfetch:license:threshold",
                                "value": "0.80"
                            },
                            {
                                "name": "dfetch:license:tool",
                                "value": "<infer-license-version>"
                            }
                        ],
                        "evidence": {
                            "licenses": [
                                {
                                    "license": {
                                        "id": "NOASSERTION",
                                        "acknowledgement": "concluded",
                                        "text": {
                                            "content": "No license file found in source tree",
                                            "contentType": "text/plain"
                                        }
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
            """
