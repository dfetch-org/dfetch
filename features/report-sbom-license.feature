Feature: SBOM license transparency for unresolved licenses

    When *dfetch* cannot determine the license of a fetched component it sets
    the CycloneDX ``licenses`` field to ``NOASSERTION`` (rather than omitting
    it) and adds a ``dfetch:license:finding`` property that explains why.

    Two situations trigger NOASSERTION:

    * A license-like file (``LICENSE``, ``COPYING``, …) was found in the
      fetched source tree but its text could not be matched to a known SPDX
      identifier with sufficient confidence.
    * No license-like file was present in the fetched source tree at all.

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
                                "expression": "NOASSERTION"
                            }
                        ],
                        "properties": [
                            {
                                "name": "dfetch:license:finding",
                                "value": "License file(s) found (LICENSE) but could not be classified"
                            },
                            {
                                "name": "dfetch:license:threshold",
                                "value": "0.80"
                            },
                            {
                                "name": "dfetch:license:tool",
                                "value": "infer-license 0.2.0"
                            }
                        ],
                        "evidence": {
                            "licenses": [
                                {
                                    "expression": "NOASSERTION"
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
                                "expression": "NOASSERTION"
                            }
                        ],
                        "properties": [
                            {
                                "name": "dfetch:license:finding",
                                "value": "No license file found in source tree"
                            },
                            {
                                "name": "dfetch:license:threshold",
                                "value": "0.80"
                            },
                            {
                                "name": "dfetch:license:tool",
                                "value": "infer-license 0.2.0"
                            }
                        ],
                        "evidence": {
                            "licenses": [
                                {
                                    "expression": "NOASSERTION"
                                }
                            ]
                        }
                    }
                ]
            }
            """
