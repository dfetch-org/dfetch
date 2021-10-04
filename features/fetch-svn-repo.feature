Feature: Fetching dependencies from a svn repository

    The main functionality of *DFetch* is fetching remote dependencies.
    A key VCS that is used in the world is svn. *DFetch* makes it possible to
    fetch svn repositories, using the revision, branch, tag or a combination.
    Typically SVN repositories are set-up with a standard layout.
    This means there is a 'trunk', 'branches/' and 'tags/'.
    Sometimes people don't do this, a user should be able to check
    a non-standard SVN repository as well.

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
                  dst: ext/test-rev-and branch

                - name: ext/test-repo-tag-v1
                  tag: v1
                  vcs: svn
                  dst: ext/test-repo-tag-v1

            """
        When I run "dfetch update"
        Then the following projects are fetched
            | path                       |
            | ext/test-repo-rev-only     |
            | ext/test-rev-and branch    |
            | ext/test-repo-tag-v1       |

    Scenario: Directory in a non-standard SVN repository can be fetched
        Given the manifest 'dfetch.yaml' in MyProject
            """
            manifest:
                version: 0.0
                projects:
                    - name: SomeProject
                      url: some-remote-server/SomeProject
                      src: SomeFolder/
                      branch: ' '
            """
        And a non-standard svn-server "SomeProject" with the files
            | path                                  |
            | SomeFolder/SomeFile.txt               |
            | SomeOtherFolder/SomeOtherFile.txt     |
        When I run "dfetch update"
        Then 'MyProject' looks like:
            """
            MyProject/
                SomeProject/
                    .dfetch_data.yaml
                    SomeFile.txt
                dfetch.yaml
            """
