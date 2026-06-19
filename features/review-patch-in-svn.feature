@review-patch
Feature: Review patches in svn

    When working with external projects that have patch files inside an SVN
    superproject, the ``review-patch`` command allows the user to inspect what
    a patch contributes.  Because SVN has no staging area, the command cannot
    use the index trick available in Git; it simply sets the working copy to
    the requested patch state and restores the original state afterwards.

    Background:
        Given a svn-server "SomeProject"
        And the patch file 'MySvnProject/patches/SomeProject.patch'
            """
            Index: README.md
            ===================================================================
            --- README.md
            +++ README.md
            @@ -1,1 +1,1 @@
            -Generated file for SomeProject
            +Patched file for SomeProject
            """
        And a fetched and committed MySvnProject with the manifest
            """
            manifest:
                version: 0.0
                projects:
                  - name: SomeProject
                    url: some-remote-server/SomeProject
                    patch: patches/SomeProject.patch
                    vcs: svn
            """

    Scenario: All patches are set up for review and state is restored afterwards
        When I run "dfetch review-patch SomeProject" in MySvnProject
        Then the output shows
            """
            Dfetch (0.14.0)
            review-patch has limited support in SVN superprojects (no staging area — use `svn diff` to inspect changes)
              SomeProject:
              > Fetched trunk - 1
              > Applying patch "patches/SomeProject.patch"
                successfully patched 1/1:    b'README.md'
              > stage = upstream, working tree = 1 patch(es) applied — open your editor and run `svn diff` to inspect
              > restored
            """
        And the patched 'MySvnProject/SomeProject/README.md' is
            """
            Patched file for SomeProject
            """

    Scenario: Only the first N patches are applied with --count
        When I run "dfetch review-patch --count 0 SomeProject" in MySvnProject
        Then the output shows
            """
            Dfetch (0.14.0)
            review-patch has limited support in SVN superprojects (no staging area — use `svn diff` to inspect changes)
              SomeProject:
              > Fetched trunk - 1
              > stage = upstream, working tree = 0 patch(es) applied — open your editor and run `svn diff` to inspect
              > Fetched trunk - 1
              > Applying patch "patches/SomeProject.patch"
                successfully patched 1/1:    b'README.md'
              > restored
            """
        And the patched 'MySvnProject/SomeProject/README.md' is
            """
            Patched file for SomeProject
            """
