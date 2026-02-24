Feature: Update an existing patch in svn

    If working with external projects, local changes can be tracked using
    patch files. If those local changes evolve over time, *Dfetch* should allow
    the user to update an existing patch so that it reflects the current working
    copy of the project.

    The update process must be safe, reproducible, and leave the project in a
    patched state matching the manifest configuration.

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

    Scenario: Patch is updated with new local changes
        Given "SomeProject/README.md" in MySvnProject is changed, added and committed with
            """
            Update to patched file for SomeProject
            """
        When I run "dfetch update-patch SomeProject" in MySvnProject
        Then the patch file 'MySvnProject/patches/SomeProject.patch' is updated
            """
            Index: README.md
            ===================================================================
            --- README.md
            +++ README.md
            @@ -1,1 +1,2 @@
            -Generated file for SomeProject
            +Patched file for SomeProject
            +Update to patched file for SomeProject

            """
        And the output shows
            """
            Dfetch (0.12.1)
            Update patch is only fully supported in git superprojects!
              SomeProject:
              > Fetched trunk - 1
              > Updating patch "patches/SomeProject.patch"
              > Fetched trunk - 1
              > Applying patch "patches/SomeProject.patch"
                successfully patched 1/1:    b'README.md'
            """

    Scenario: Patch is updated with new but not ignored files
        Given files as '*.tmp' are ignored in 'MySvnProject/SomeProject' in svn
        And "SomeProject/IGNORE_ME.tmp" in MySvnProject is created
        And all files in MySvnProject are added and committed
        When I run "dfetch update-patch SomeProject" in MySvnProject
        Then the patch file 'MySvnProject/patches/SomeProject.patch' is updated
            """
            Index: README.md
            ===================================================================
            --- README.md
            +++ README.md
            @@ -1,1 +1,1 @@
            -Generated file for SomeProject
            +Patched file for SomeProject

            """
