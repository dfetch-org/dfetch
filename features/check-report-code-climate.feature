Feature: Let check report to code climate

    *DFetch* can check if there are new versions available. Since this is an action a developer
    might not perform daily, it is possible to perform a check and generate a report that code-climate
    and Gitlab can interpret.

    Scenario: A newer tag is available than in manifest
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              remotes:
                - name: github-com-dfetch-org
                  url-base: https://github.com/dfetch-org/test-repo

              projects:
                - name: ext/test-repo-tag-v1
                  tag: v1
                  dst: ext/test-repo-tag-v1

            """
        When I run "dfetch check --code-climate code_climate.json"
        Then the 'code_climate.json' file contains
            """
            [
                {
                    "description": "The manifest requires version 'v1' of ext/test-repo-tag-v1. it was never fetched, fetch it with 'dfetch update ext/test-repo-tag-v1. The latest version available is 'v2.0'",
                    "check_name": "unfetched-project",
                    "categories": [
                        "Security",
                        "Bug risk"
                    ],
                    "fingerprint": "2cc525a6d825f2dc541ade86dfdd351a1a7c47c2b41f3d31fa9b7b19f9400006",
                    "severity": "major",
                    "location": {
                        "path": "dfetch.yaml",
                        "positions": {
                            "begin": {
                                "line": 9,
                                "column": 13
                            },
                            "end": {
                                "line": 9,
                                "column": 32
                            }
                        }
                    }
                }
            ]
            """

    Scenario: Check is done after an update
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              remotes:
                - name: github-com-dfetch-org
                  url-base: https://github.com/dfetch-org/test-repo

              projects:
                - name: ext/test-repo-rev-only
                  revision: e1fda19a57b873eb8e6ae37780594cbb77b70f1a
                  dst: ext/test-repo-rev-only

                - name: ext/test-rev-and-branch
                  revision: 8df389d0524863b85f484f15a91c5f2c40aefda1
                  branch: main
                  dst: ext/test-rev-and-branch

            """
        And all projects are updated
        When I run "dfetch check --code-climate code_climate.json"
        Then the 'code_climate.json' file contains
            """
            [
                {
                    "description": "The manifest requires version 'e1fda19a57b873eb8e6ae37780594cbb77b70f1a' of ext/test-repo-rev-only. Currently version 'master - e1fda19a57b873eb8e6ae37780594cbb77b70f1a' is present. There is a newer version available 'master'. Please update using 'dfetch update ext/test-repo-rev-only.",
                    "check_name": "out-of-date-project",
                    "categories": [
                        "Security",
                        "Bug risk"
                    ],
                    "fingerprint": "443fbc33d4f9c5cc7a9ed34e31ec786f10c20e64c7480aff59d7947ad5e23c8a",
                    "severity": "minor",
                    "location": {
                        "path": "dfetch.yaml",
                        "positions": {
                            "begin": {
                                "line": 9,
                                "column": 13
                            },
                            "end": {
                                "line": 9,
                                "column": 34
                            }
                        }
                    }
                },
                {
                    "description": "The manifest requires version 'main - 8df389d0524863b85f484f15a91c5f2c40aefda1' of ext/test-rev-and-branch. This is also the current version. There is a newer version available 'main - e1fda19a57b873eb8e6ae37780594cbb77b70f1a' You can update the version in the manifest and run 'dfetch update ext/test-rev-and-branch'",
                    "check_name": "pinned-but-out-of-date-project",
                    "categories": [
                        "Security",
                        "Bug risk"
                    ],
                    "fingerprint": "ea830628ce63a7d3331e72ce95fa7cd7b2017ed2f17c1e77445d7a3cde140af3",
                    "severity": "info",
                    "location": {
                        "path": "dfetch.yaml",
                        "positions": {
                            "begin": {
                                "line": 13,
                                "column": 13
                            },
                            "end": {
                                "line": 13,
                                "column": 35
                            }
                        }
                    }
                }
            ]
            """

    Scenario: Tag is updated in manifest
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              projects:
                - name: ext/test-repo-tag
                  url: https://github.com/dfetch-org/test-repo
                  tag: v1

            """
        And all projects are updated
        When the manifest 'dfetch.yaml' is changed to
            """
            manifest:
              version: '0.0'

              projects:
                - name: ext/test-repo-tag
                  url: https://github.com/dfetch-org/test-repo
                  tag: v2.0

            """
        And I run "dfetch check --code-climate code_climate.json"
        Then the 'code_climate.json' file contains
            """
            [
                {
                    "description": "The manifest requires version 'v2.0' of ext/test-repo-tag. Currently version 'v1' is present. There is a newer version available 'v2.0'. Please update using 'dfetch update ext/test-repo-tag.",
                    "check_name": "out-of-date-project",
                    "categories": [
                        "Security",
                        "Bug risk"
                    ],
                    "fingerprint": "14879c573e42bdc3ef8feb7ea73f23b0894839b859b713dabaf4efa1b4f2537a",
                    "severity": "minor",
                    "location": {
                        "path": "dfetch.yaml",
                        "positions": {
                            "begin": {
                                "line": 5,
                                "column": 13
                            },
                            "end": {
                                "line": 5,
                                "column": 29
                            }
                        }
                    }
                }
            ]
            """

    Scenario: A local change is reported
        Given a git repository "SomeProject.git"
        And a fetched and committed MyProject with the manifest
            """
            manifest:
                version: 0.0
                projects:
                  - name: SomeProject
                    url: some-remote-server/SomeProject.git
            """
        And "SomeProject/README.md" in MyProject is changed and committed with
            """
            An important sentence for the README!
            """
        When I run "dfetch check --code-climate code_climate.json SomeProject" in MyProject
        Then the 'MyProject/code_climate.json' file contains
            """
            [
                {
                    "description": "SomeProject has local changes, please create a patch file using 'dfetch diff SomeProject. This patch file can either be used to directly from the manifest using the patch attribute, or upstreamed.",
                    "check_name": "local-changes-in-project",
                    "categories": [
                        "Security",
                        "Bug risk"
                    ],
                    "fingerprint": "c9e65f37627d383daf06893c932080d554ef8b9578b81e6d2914f04f0a18c120",
                    "severity": "minor",
                    "location": {
                        "path": "dfetch.yaml",
                        "positions": {
                            "begin": {
                                "line": 4,
                                "column": 15
                            },
                            "end": {
                                "line": 4,
                                "column": 25
                            }
                        }
                    }
                }
            ]
            """
