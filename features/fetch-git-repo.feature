Feature: Fetching dependencies from a git repository

    The main functionality of *DFetch* is fetching remote dependencies.
    A key VCS that is used in the world is git. *DFetch* makes it possible to
    fetch git repositories, using the revision, branch, tag or a combination.

    Scenario: Git projects are specified in the manifest
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

                - name: ext/test-repo-tag-v1
                  tag: v1
                  dst: ext/test-repo-tag-v1

            """
        When I run "dfetch update"
        Then the following projects are fetched
            | path                       |
            | ext/test-repo-rev-only     |
            | ext/test-rev-and-branch    |
            | ext/test-repo-tag-v1       |

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
        And I run "dfetch update"
        Then the output shows
            """
            Dfetch (0.8.0)
              ext/test-repo-tag   : Fetched v2.0
            """

    Scenario: Version check ignored when force flag is given
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
        When I run "dfetch update --force"
        Then the output shows
            """
            Dfetch (0.8.0)
              ext/test-repo-tag   : Fetched v1
            """
