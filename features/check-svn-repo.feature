Feature: Checking dependencies from a svn repository

    *DFetch* can check if there are new versions.

    Scenario: SVN projects are specified in the manifest
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              remotes:
                - name: github-com-dfetch-org
                  url-base: https://github.com/dfetch-org/test-repo

              projects:
                - name: ext/test-repo-rev-only
                  revision: '2'
                  vcs: svn
                  dst: ext/test-repo-rev-only

                - name: ext/test-rev-and-branch
                  revision: '1'
                  vcs: svn
                  branch: trunk
                  dst: ext/test-rev-and-branch

            """
        When I run "dfetch check"
        Then the output shows
            """
            Dfetch (0.0.6)
              ext/test-repo-rev-only: wanted (2), available (trunk - 4)
              ext/test-rev-and-branch: wanted (trunk - 1), available (trunk - 4)
            """

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
                  vcs: svn
                  tag: v1
                  dst: ext/test-repo-tag-v1

            """
        When I run "dfetch check"
        Then the output shows
            """
            Dfetch (0.0.6)
              ext/test-repo-tag-v1: wanted (v1), available (v2.0)
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
                  revision: '2'
                  vcs: svn
                  dst: ext/test-repo-rev-only

                - name: ext/test-rev-and-branch
                  revision: '1'
                  vcs: svn
                  branch: trunk
                  dst: ext/test-rev-and-branch

            """
        And all projects are updated
        When I run "dfetch check"
        Then the output shows
            """
            Dfetch (0.0.7)
              ext/test-repo-rev-only: wanted (2), current (trunk - 2), available (trunk - 4)
              ext/test-rev-and-branch: wanted & current (trunk - 1), available (trunk - 4)
            """
