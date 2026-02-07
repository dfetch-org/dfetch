Feature: Formatting a patch for svn repositories

    If a project is fetched from a svn repository, and changes are made to
    that project, *DFetch* should be able to create a patch file that can be
    applied to the original repository. This way the upstream repository can
    be kept up to date with local changes.

    Scenario: All patch files are formatted
        Given a svn-server "SomeProject" with the files
            | path                                     |
            | SomeFolder/SomeSubFolder/README.md       |
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
                    src: SomeFolder/SomeSubFolder
                    patch:
                      -  patches/001-diff.patch
                      -  patches/002-diff.patch
                    vcs: svn
            """
        And all projects are updated
        When I run "dfetch format-patch SomeProject --output-directory formatted-patches" in MySvnProject
        Then the patch file 'MySvnProject/formatted-patches/001-diff.patch' is generated
            """
            Index: SomeFolder/SomeSubFolder/README.md
            ===================================================================
            --- SomeFolder/SomeSubFolder/README.md
            +++ SomeFolder/SomeSubFolder/README.md
            @@ -1,1 +1,1 @@
            -Generated file for SomeProject
            +Patched file for SomeProject

            """
        And the patch file 'MySvnProject/formatted-patches/002-diff.patch' is generated
            """
            Index: SomeFolder/SomeSubFolder/README.md
            ===================================================================
            --- SomeFolder/SomeSubFolder/README.md
            +++ SomeFolder/SomeSubFolder/README.md
            @@ -1,1 +1,1 @@
            -Generated file for SomeProject
            +Patched file for formatted patch of SomeProject
            """

    Scenario: Git subproject in Svn superproject gives a git patch
        Given a git repository "SomeProject.git"
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
        And a fetched and committed MySvnProject with the manifest
            """
            manifest:
                version: 0.0
                projects:
                  - name: some-subproject
                    url: some-remote-server/SomeProject.git
                    patch:
                      -  patches/001-diff.patch
            """
        When I run "dfetch format-patch some-subproject --output-directory MySvnProject/patches"
        Then the patch file 'MySvnProject/patches/001-diff.patch' is generated
            """
            From ce0f26a0ef7924942debe7285af89337bac26ddf Mon Sep 17 00:00:00 2001
            From: ben <ben@example.com>
            Date: Sat, 07 Feb 2026 16:23:34 +0000
            Subject: [PATCH] Patch for some-subproject

            Patch for some-subproject

            diff --git a/README.md b/README.md
            --- a/README.md
            +++ b/README.md
            @@ -1,1 +1,1 @@
            -Generated file for SomeProject
            +Patched file for SomeProject

            """
