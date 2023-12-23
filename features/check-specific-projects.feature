Feature: Checking specific projects

    *DFetch* can check specific projects, this is useful when you have a lot
    of projects in your manifest.

    Scenario: Single project is checked
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
        When I run "dfetch check ext/test-rev-and-branch"
        Then the output shows
            """
            Dfetch (0.8.0)
              ext/test-rev-and-branch: wanted (main - 8df389d0524863b85f484f15a91c5f2c40aefda1), available (main - e1fda19a57b873eb8e6ae37780594cbb77b70f1a)
            """
