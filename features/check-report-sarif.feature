Feature: Let check report to sarif

    *DFetch* can check if there are new versions available. Since this is an action a developer
    might not perform daily, it is possible to perform a check and generate a report that sarif
    can interpret.

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
        When I run "dfetch check --sarif sarif.json"
        Then the 'sarif.json' file contains
            """
            {
                "runs": [
                    {
                        "tool": {
                            "driver": {
                                "name": "DFetch",
                                "informationUri": "https://dfetch.rtfd.io",
                                "rules": [
                                    {
                                        "id": "unfetched-project",
                                        "help": {
                                            "text": "The project mentioned in the manifest was never fetched, fetch it with 'dfetch update <project>'. After fetching, commit the updated project to your repository."
                                        },
                                        "shortDescription": {
                                            "text": "Project was never fetched"
                                        }
                                    },
                                    {
                                        "id": "up-to-date-project",
                                        "help": {
                                            "text": "The project mentioned in the manifest is up-to-date, everything is ok, nothing to do."
                                        },
                                        "shortDescription": {
                                            "text": "Project is up-to-date"
                                        }
                                    },
                                    {
                                        "id": "pinned-but-out-of-date-project",
                                        "help": {
                                            "text": "The project mentioned in the manifest is pinned to a specific version, For instance a branch, tag, or revision. This is currently the state of the project. However a newer version is available at the upstream of the project. Either ignore this warning or update the version to the latest and update using 'dfetch update <project>' and commit the result to your repository."
                                        },
                                        "shortDescription": {
                                            "text": "Project is pinned, but out-of-date"
                                        }
                                    },
                                    {
                                        "id": "out-of-date-project",
                                        "help": {
                                            "text": "The project is configured to always follow the latest version, There is a newer version available at the upstream of the project. Please update the project using 'dfetch update <project>' and commit the result to your repository."
                                        },
                                        "shortDescription": {
                                            "text": "Project is out-of-date"
                                        }
                                    },
                                    {
                                        "id": "local-changes-in-project",
                                        "help": {
                                            "text": "The files of this project are different then when they were added, Please create a patch using 'dfetch diff <project>' and add it to the manifest using the 'patch:' attribute. Or better yet, upstream the changes and update your project. When running 'dfetch check' on a platform with different line endings, then this warning is likely a false positive."
                                        },
                                        "shortDescription": {
                                            "text": "Project was locally changed"
                                        }
                                    }
                                ]
                            }
                        },
                        "artifacts": [
                            {
                                "location": {
                                    "uri": "dfetch.yaml"
                                },
                                "sourceLanguage": "yaml"
                            }
                        ],
                        "results": [
                            {
                                "message": {
                                    "text": "ext/test-repo-tag-v1 : ext/test-repo-tag-v1 was never fetched!"
                                },
                                "level": "error",
                                "locations": [
                                    {
                                        "physicalLocation": {
                                            "artifactLocation": {
                                                "index": 0,
                                                "uri": "dfetch.yaml"
                                            },
                                            "region": {
                                                "endColumn": 33,
                                                "endLine": 9,
                                                "startColumn": 13,
                                                "startLine": 9
                                            }
                                        }
                                    }
                                ],
                                "ruleId": "unfetched-project"
                            }
                        ]
                    }
                ],
                "version": "2.1.0"
            }
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
        When I run "dfetch check --sarif sarif.json"
        Then the 'sarif.json' file contains
            """
            {
                "runs": [
                    {
                        "tool": {
                            "driver": {
                                "name": "DFetch",
                                "informationUri": "https://dfetch.rtfd.io",
                                                                "rules": [
                                    {
                                        "id": "unfetched-project",
                                        "help": {
                                            "text": "The project mentioned in the manifest was never fetched, fetch it with 'dfetch update <project>'. After fetching, commit the updated project to your repository."
                                        },
                                        "shortDescription": {
                                            "text": "Project was never fetched"
                                        }
                                    },
                                    {
                                        "id": "up-to-date-project",
                                        "help": {
                                            "text": "The project mentioned in the manifest is up-to-date, everything is ok, nothing to do."
                                        },
                                        "shortDescription": {
                                            "text": "Project is up-to-date"
                                        }
                                    },
                                    {
                                        "id": "pinned-but-out-of-date-project",
                                        "help": {
                                            "text": "The project mentioned in the manifest is pinned to a specific version, For instance a branch, tag, or revision. This is currently the state of the project. However a newer version is available at the upstream of the project. Either ignore this warning or update the version to the latest and update using 'dfetch update <project>' and commit the result to your repository."
                                        },
                                        "shortDescription": {
                                            "text": "Project is pinned, but out-of-date"
                                        }
                                    },
                                    {
                                        "id": "out-of-date-project",
                                        "help": {
                                            "text": "The project is configured to always follow the latest version, There is a newer version available at the upstream of the project. Please update the project using 'dfetch update <project>' and commit the result to your repository."
                                        },
                                        "shortDescription": {
                                            "text": "Project is out-of-date"
                                        }
                                    },
                                    {
                                        "id": "local-changes-in-project",
                                        "help": {
                                            "text": "The files of this project are different then when they were added, Please create a patch using 'dfetch diff <project>' and add it to the manifest using the 'patch:' attribute. Or better yet, upstream the changes and update your project. When running 'dfetch check' on a platform with different line endings, then this warning is likely a false positive."
                                        },
                                        "shortDescription": {
                                            "text": "Project was locally changed"
                                        }
                                    }
                                ]
                            }
                        },
                        "artifacts": [
                            {
                                "location": {
                                    "uri": "dfetch.yaml"
                                },
                                "sourceLanguage": "yaml"
                            }
                        ],
                        "results": [
                            {
                                "message": {
                                    "text": "ext/test-repo-rev-only : ext/test-repo-rev-only current version is 'master - e1fda19a57b873eb8e6ae37780594cbb77b70f1a', the wanted version is 'e1fda19a57b873eb8e6ae37780594cbb77b70f1a', but 'master' is available."
                                },
                                "level": "warning",
                                "locations": [
                                    {
                                        "physicalLocation": {
                                            "artifactLocation": {
                                                "index": 0,
                                                "uri": "dfetch.yaml"
                                            },
                                            "region": {
                                                "endColumn": 35,
                                                "endLine": 9,
                                                "startColumn": 13,
                                                "startLine": 9
                                            }
                                        }
                                    }
                                ],
                                "ruleId": "out-of-date-project"
                            },
                            {
                                "message": {
                                    "text": "ext/test-rev-and-branch : ext/test-rev-and-branch wanted & current version is 'main - 8df389d0524863b85f484f15a91c5f2c40aefda1', but 'main - e1fda19a57b873eb8e6ae37780594cbb77b70f1a' is available."
                                },
                                "level": "note",
                                "locations": [
                                    {
                                        "physicalLocation": {
                                            "artifactLocation": {
                                                "index": 0,
                                                "uri": "dfetch.yaml"
                                            },
                                            "region": {
                                                "endColumn": 36,
                                                "endLine": 13,
                                                "startColumn": 13,
                                                "startLine": 13
                                            }
                                        }
                                    }
                                ],
                                "ruleId": "pinned-but-out-of-date-project"
                            }
                        ]
                    }
                ],
                "version": "2.1.0"
            }
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
        And I run "dfetch check --sarif sarif.json"
        Then the 'sarif.json' file contains
        """
        {
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "DFetch",
                            "informationUri": "https://dfetch.rtfd.io",
                                                            "rules": [
                                    {
                                        "id": "unfetched-project",
                                        "help": {
                                            "text": "The project mentioned in the manifest was never fetched, fetch it with 'dfetch update <project>'. After fetching, commit the updated project to your repository."
                                        },
                                        "shortDescription": {
                                            "text": "Project was never fetched"
                                        }
                                    },
                                    {
                                        "id": "up-to-date-project",
                                        "help": {
                                            "text": "The project mentioned in the manifest is up-to-date, everything is ok, nothing to do."
                                        },
                                        "shortDescription": {
                                            "text": "Project is up-to-date"
                                        }
                                    },
                                    {
                                        "id": "pinned-but-out-of-date-project",
                                        "help": {
                                            "text": "The project mentioned in the manifest is pinned to a specific version, For instance a branch, tag, or revision. This is currently the state of the project. However a newer version is available at the upstream of the project. Either ignore this warning or update the version to the latest and update using 'dfetch update <project>' and commit the result to your repository."
                                        },
                                        "shortDescription": {
                                            "text": "Project is pinned, but out-of-date"
                                        }
                                    },
                                    {
                                        "id": "out-of-date-project",
                                        "help": {
                                            "text": "The project is configured to always follow the latest version, There is a newer version available at the upstream of the project. Please update the project using 'dfetch update <project>' and commit the result to your repository."
                                        },
                                        "shortDescription": {
                                            "text": "Project is out-of-date"
                                        }
                                    },
                                    {
                                        "id": "local-changes-in-project",
                                        "help": {
                                            "text": "The files of this project are different then when they were added, Please create a patch using 'dfetch diff <project>' and add it to the manifest using the 'patch:' attribute. Or better yet, upstream the changes and update your project. When running 'dfetch check' on a platform with different line endings, then this warning is likely a false positive."
                                        },
                                        "shortDescription": {
                                            "text": "Project was locally changed"
                                        }
                                    }
                                ]
                        }
                    },
                    "artifacts": [
                        {
                            "location": {
                                "uri": "dfetch.yaml"
                            },
                            "sourceLanguage": "yaml"
                        }
                    ],
                    "results": [
                        {
                            "message": {
                                "text": "ext/test-repo-tag : ext/test-repo-tag current version is 'v1', the wanted version is 'v2.0', but 'v2.0' is available."
                            },
                            "level": "warning",
                            "locations": [
                                {
                                    "physicalLocation": {
                                        "artifactLocation": {
                                            "index": 0,
                                            "uri": "dfetch.yaml"
                                        },
                                        "region": {
                                            "endColumn": 30,
                                            "endLine": 5,
                                            "startColumn": 13,
                                            "startLine": 5
                                        }
                                    }
                                }
                            ],
                            "ruleId": "out-of-date-project"
                        }
                    ]
                }
            ],
            "version": "2.1.0"
        }
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
        When I run "dfetch check --sarif sarif.json SomeProject" in MyProject
        Then the 'MyProject/sarif.json' file contains
        """
        {
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "DFetch",
                            "informationUri": "https://dfetch.rtfd.io",
                            "rules": [
                                {
                                    "id": "unfetched-project",
                                    "help": {
                                        "text": "The project mentioned in the manifest was never fetched, fetch it with 'dfetch update <project>'. After fetching, commit the updated project to your repository."
                                    },
                                    "shortDescription": {
                                        "text": "Project was never fetched"
                                    }
                                },
                                {
                                    "id": "up-to-date-project",
                                    "help": {
                                        "text": "The project mentioned in the manifest is up-to-date, everything is ok, nothing to do."
                                    },
                                    "shortDescription": {
                                        "text": "Project is up-to-date"
                                    }
                                },
                                {
                                    "id": "pinned-but-out-of-date-project",
                                    "help": {
                                        "text": "The project mentioned in the manifest is pinned to a specific version, For instance a branch, tag, or revision. This is currently the state of the project. However a newer version is available at the upstream of the project. Either ignore this warning or update the version to the latest and update using 'dfetch update <project>' and commit the result to your repository."
                                    },
                                    "shortDescription": {
                                        "text": "Project is pinned, but out-of-date"
                                    }
                                },
                                {
                                    "id": "out-of-date-project",
                                    "help": {
                                        "text": "The project is configured to always follow the latest version, There is a newer version available at the upstream of the project. Please update the project using 'dfetch update <project>' and commit the result to your repository."
                                    },
                                    "shortDescription": {
                                        "text": "Project is out-of-date"
                                    }
                                },
                                {
                                    "id": "local-changes-in-project",
                                    "help": {
                                        "text": "The files of this project are different then when they were added, Please create a patch using 'dfetch diff <project>' and add it to the manifest using the 'patch:' attribute. Or better yet, upstream the changes and update your project. When running 'dfetch check' on a platform with different line endings, then this warning is likely a false positive."
                                    },
                                    "shortDescription": {
                                        "text": "Project was locally changed"
                                    }
                                }
                            ]
                        }
                    },
                    "artifacts": [
                        {
                            "location": {
                                "uri": "dfetch.yaml"
                            },
                            "sourceLanguage": "yaml"
                        }
                    ],
                    "results": [
                        {
                            "message": {
                                "text": "SomeProject : SomeProject has local changes, please create a patch file or upstream the changes."
                            },
                            "level": "warning",
                            "locations": [
                                {
                                    "physicalLocation": {
                                        "artifactLocation": {
                                            "index": 0,
                                            "uri": "dfetch.yaml"
                                        },
                                        "region": {
                                            "endColumn": 26,
                                            "endLine": 4,
                                            "startColumn": 15,
                                            "startLine": 4
                                        }
                                    }
                                }
                            ],
                            "ruleId": "local-changes-in-project"
                        }
                    ]
                }
            ],
            "version": "2.1.0"
        }
            """
