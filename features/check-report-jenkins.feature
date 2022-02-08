Feature: Let check report to jenkins

    *DFetch* can check if there are new versions available. Since this is an action a developer
    might not perform daily, it is possible to perform a check and generate a report that jenkins
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
        When I run "dfetch check --jenkins-json jenkins.json"
        Then the 'jenkins.json' file contains
            """
            {
                "_class": "io.jenkins.plugins.analysis.core.restapi.ReportApi",
                "issues": [
                    {
                        "fileName": "dfetch.yaml",
                        "severity": "High",
                        "message": "ext/test-repo-tag-v1 : ext/test-repo-tag-v1 was never fetched!",
                        "description": "The manifest requires version 'v1' of ext/test-repo-tag-v1. it was never fetched, fetch it with 'dfetch update ext/test-repo-tag-v1. The latest version available is 'v2.0'",
                        "lineStart": 9,
                        "lineEnd": 9,
                        "columnStart": 13,
                        "columnEnd": 32
                    }
                ]
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
        When I run "dfetch check --jenkins-json jenkins.json"
        Then the 'jenkins.json' file contains
            """
            {
                "_class": "io.jenkins.plugins.analysis.core.restapi.ReportApi",
                "issues": [
                    {
                        "fileName": "dfetch.yaml",
                        "severity": "Normal",
                        "message": "ext/test-repo-rev-only : ext/test-repo-rev-only current version is 'master - e1fda19a57b873eb8e6ae37780594cbb77b70f1a', the wanted version is 'e1fda19a57b873eb8e6ae37780594cbb77b70f1a', but 'master' is available.",
                        "description": "The manifest requires version 'e1fda19a57b873eb8e6ae37780594cbb77b70f1a' of ext/test-repo-rev-only. Currently version 'master - e1fda19a57b873eb8e6ae37780594cbb77b70f1a' is present. There is a newer version available 'master'. Please update using 'dfetch update ext/test-repo-rev-only.",
                        "lineStart": 9,
                        "lineEnd": 9,
                        "columnStart": 13,
                        "columnEnd": 34
                    },
                    {
                        "fileName": "dfetch.yaml",
                        "severity": "Low",
                        "message": "ext/test-rev-and-branch : ext/test-rev-and-branch wanted & current version is 'main - 8df389d0524863b85f484f15a91c5f2c40aefda1', but 'main - e1fda19a57b873eb8e6ae37780594cbb77b70f1a' is available.",
                        "description": "The manifest requires version 'main - 8df389d0524863b85f484f15a91c5f2c40aefda1' of ext/test-rev-and-branch. This is also the current version. There is a newer version available 'main - e1fda19a57b873eb8e6ae37780594cbb77b70f1a' You can update the version in the manifest and run 'dfetch update ext/test-rev-and-branch'",
                        "lineStart": 13,
                        "lineEnd": 13,
                        "columnStart": 13,
                        "columnEnd": 35
                    }
                ]
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
        And I run "dfetch check --jenkins-json jenkins.json"
        Then the 'jenkins.json' file contains
            """
            {
                "_class": "io.jenkins.plugins.analysis.core.restapi.ReportApi",
                "issues": [
                    {
                        "fileName": "dfetch.yaml",
                        "severity": "Normal",
                        "message": "ext/test-repo-tag : ext/test-repo-tag current version is 'v1', the wanted version is 'v2.0', but 'v2.0' is available.",
                        "description": "The manifest requires version 'v2.0' of ext/test-repo-tag. Currently version 'v1' is present. There is a newer version available 'v2.0'. Please update using 'dfetch update ext/test-repo-tag.",
                        "lineStart": 5,
                        "lineEnd": 5,
                        "columnStart": 13,
                        "columnEnd": 29
                    }
                ]
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
        When I run "dfetch check --jenkins-json jenkins.json SomeProject" in MyProject
        Then the 'MyProject/jenkins.json' file contains
            """
            {
                "_class": "io.jenkins.plugins.analysis.core.restapi.ReportApi",
                "issues": [
                    {
                        "fileName": "dfetch.yaml",
                        "severity": "Normal",
                        "message": "SomeProject : SomeProject has local changes, please create a patch file or upstream the changes.",
                        "description": "SomeProject has local changes, please create a patch file using 'dfetch diff SomeProject. This patch file can either be used to directly from the manifest using the patch attribute, or upstreamed.",
                        "lineStart": 4,
                        "lineEnd": 4,
                        "columnStart": 15,
                        "columnEnd": 25
                    }
                ]
            }
            """
