Feature: Fetching specific dependencies

    *DFetch* can update specific projects, this is useful when you have a lot
    of projects in your manifest.

    Scenario: Two Specific projects are fetched
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
        When I run "dfetch update ext/test-repo-tag-v1 ext/test-rev-and-branch"
        Then the following projects are fetched
            | path                       |
            | ext/test-rev-and-branch    |
            | ext/test-repo-tag-v1       |
