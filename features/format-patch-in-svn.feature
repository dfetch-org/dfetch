Feature: Formatting a patch for svn repositories

    If a project is fetched from a svn repository, and changes are made to
    that project, *DFetch* should be able to create a patch file that can be
    applied to the original repository. This way the upstream repository can
    be kept up to date with local changes.

    Scenario: All patch files are formatted
        Given a svn-server "SomeProject"
        And the patch file 'MySvnProject/patches/001-diff.patch'
            """
            Index: README.md
            ===================================================================
            --- README.md
            +++ README.md
            @@ -1,1 +1,1 @@
            -Generated file for SomeProject
            +Patched file for SomeProject
            """
        And the patch file 'MySvnProject/patches/002-diff.patch'
            """
            Index: README.md
            ===================================================================
            --- README.md
            +++ README.md
            @@ -1,1 +1,1 @@
            -Generated file for SomeProject
            +Patched file for formatted patch of SomeProject
            """
        And a fetched and committed MySvnProject with the manifest
            """
            manifest:
                version: 0.0
                projects:
                  - name: SomeProject
                    url: some-remote-server/SomeProject
                    patch:
                      -  patches/001-diff.patch
                      -  patches/002-diff.patch
                    vcs: svn
            """
        And all projects are updated
        When I run "dfetch format-patch SomeProject --output-directory formatted-patches" in MySvnProject
        Then the patch file 'MySvnProject/formatted-patches/001-diff.patch' is generated
            """

            Index: a/README.md
            ===================================================================
            --- a/README.md
            +++ b/README.md
            @@ -1,1 +1,1 @@
            -Generated file for SomeProject
            +Patched file for SomeProject

            """
        And the patch file 'MySvnProject/formatted-patches/002-diff.patch' is generated
            """

            Index: a/README.md
            ===================================================================
            --- a/README.md
            +++ b/README.md
            @@ -1,1 +1,1 @@
            -Generated file for SomeProject
            +Patched file for formatted patch of SomeProject
            """
