Feature: Importing submodules from an existing git repository

    One alternative to *Dfetch* is git submodules. To make the transition
    as easy as possible, a user should be able to generate a manifest that
    is filled with the submodules and their pinned versions.

    Scenario: Multiple submodules are imported
        Given a git repo with the following submodules
            | path           | url                                     | revision                                 |
            | ext/test-repo1 | https://github.com/dfetch-org/test-repo | e1fda19a57b873eb8e6ae37780594cbb77b70f1a |
            | ext/test-repo2 | https://github.com/dfetch-org/test-repo | 8df389d0524863b85f484f15a91c5f2c40aefda1 |
        When I run "dfetch import"
        Then it should generate the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              remotes:
              - name: github-com-dfetch-org
                url-base: https://github.com/dfetch-org

              projects:
              - name: ext/test-repo1
                revision: e1fda19a57b873eb8e6ae37780594cbb77b70f1a
                branch: main
                repo-path: test-repo

              - name: ext/test-repo2
                revision: 8df389d0524863b85f484f15a91c5f2c40aefda1
                tag: v1
                repo-path: test-repo

            """
