Feature: Patch after fetching from git repo

    Sometimes a patch needs to be applied after fetching. *DFetch* makes it
    possible to specify a patch file.

    @wip
    Scenario: A patch file is applied after fetching
        Given the manifest 'dfetch.yaml'
            """
            manifest:
                version: '0.0'

                remotes:
                - name: github-com-dfetch-org
                  url-base: https://github.com/dfetch-org/test-repo

                projects:
                - name: ext/test-repo-tag
                  tag: v2.0
                  vcs: svn
                  dst: ext/test-repo-tag
                  patch: diff.patch
            """
        And the patch file 'diff.patch'
            """
            Index: README.md
            ===================================================================
            --- README.md	(revision 2)
            +++ README.md	(revision 3)
            @@ -1,2 +1,2 @@
             # Test-repo
            -A test repo for testing dfetch.
            +A test repo for testing patch.
            """
        When I run "dfetch update"
        Then the resulting file after patching should be 'ext/test-repo-tag/README.md'
            """
            # Test-repo
            A test repo for testing patch.
            """

    @wip
    Scenario: Applying patch file fails
        Given the manifest 'dfetch.yaml'
            """
            manifest:
                version: '0.0'

                remotes:
                - name: github-com-dfetch-org
                  url-base: https://github.com/dfetch-org/test-repo

                projects:
                - name: ext/test-repo-tag
                  tag: v2.0
                  vcs: svn
                  dst: ext/test-repo-tag
                  patch: diff.patch
            """
        And the patch file 'diff.patch'
            """
            Index: README.md
            ===================================================================
            --- README1.md	(revision 2)
            +++ README1.md	(revision 3)
            @@ -1,2 +1,2 @@
             # Test-repo
            -A test repo for testing dfetch.
            +A test repo for testing patch.
            """
        When I run "dfetch update"
        Then the output shows
            """
            Dfetch (0.1.0)
              ext/test-repo-tag   : Fetched v2.0
            source/target file does not exist:
              --- b'README1.md'
              +++ b'README1.md'
              ext/test-repo-tag   : Applying path "diff.patch" failed
            """