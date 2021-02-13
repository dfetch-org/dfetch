Feature: Fetching dependencies from a svn repository

    The main functionality of *DFetch* is fetching remote dependencies.
    A key VCS that is used in the world is svn. *DFetch* makes it possible to
    fetch svn repositories, using the revision, branch, tag or a combination.

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
                  revision: '1'
                  vcs: svn
                  dst: ext/test-repo-rev-only

                - name: ext/test-rev-and-branch
                  revision: '2'
                  branch: trunk
                  vcs: svn
                  dst: ext/test-rev-and-branch

                - name: ext/test-repo-tag-v1
                  tag: v1
                  vcs: svn
                  dst: ext/test-repo-tag-v1

            """
        When I run "dfetch update"
        Then the following projects are fetched
            | path                       |
            | ext/test-repo-rev-only     |
            | ext/test-rev-and-branch    |
            | ext/test-repo-tag-v1       |
