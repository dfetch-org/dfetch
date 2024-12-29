@remote-svn
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
                - name: cunit
                  url-base: svn://svn.code.sf.net/p/cunit/code
                  default: true

                - name: cutter
                  url-base: svn://svn.code.sf.net/p/cutter/svn/cutter

              projects:
                - name: cunit-svn-rev-only
                  revision: '170'
                  vcs: svn
                  dst: ext/cunit-svn-rev-only

                - name: cunit-svn-rev-and-branch
                  revision: '156'
                  vcs: svn
                  branch: mingw64
                  dst: ext/cunit-svn-rev-and-branch

                - name: cutter-svn-tag
                  vcs: svn
                  tag: 1.1.7
                  src: acmacros
                  dst: ext/cutter-svn-tag
                  remote: cutter

            """
        When I run "dfetch update"
        Then the following projects are fetched
            | path                         |
            | ext/cunit-svn-rev-only       |
            | ext/cunit-svn-rev-and-branch |
            | ext/cutter-svn-tag           |

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
