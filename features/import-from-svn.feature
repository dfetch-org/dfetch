Feature: Importing externals from an existing svn repository

    One alternative to *Dfetch* is svn externals. To make the transition
    as easy as possible, a user should be able to generate a manifest that
    is filled with the externals and their pinned versions.

    Scenario: Multiple externals are imported
        Given a svn repo with the following externals
            | path           | url                                               | revision       |
            | ext/test-repo1 | https://github.com/dfetch-org/test-repo/trunk     | 1              |
            | ext/test-repo2 | https://github.com/dfetch-org/test-repo/tags/v2.0 |                |
            | ext/test-repo3 | https://github.com/dfetch-org/test-repo           |                |
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
                  revision: '1'
                  dst: ./ext/test-repo1
                  repo-path: test-repo

                - name: ext/test-repo2
                  dst: ./ext/test-repo2
                  tag: v2.0
                  repo-path: test-repo

                - name: ext/test-repo3
                  dst: ./ext/test-repo3
                  branch: ' '
                  repo-path: test-repo

            """
