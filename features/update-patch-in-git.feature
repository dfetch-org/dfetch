Feature: Update an existing patch in git

    If working with external projects, local changes are can be tracked using
    patch files. If those local changes evolve over time, *Dfetch* should allow
    the user to update an existing patch so that it reflects the current working
    copy of the project.

    The update process must be safe, reproducible, and leave the project in a
    patched state matching the manifest configuration.

    Background:
        Given a git repository "SomeProject.git"
        And the patch file 'MyProject/patches/SomeProject.patch'
            """
            diff --git a/README.md b/README.md
            index 32d9fad..62248b7 100644
            --- a/README.md
            +++ b/README.md
            @@ -1,1 +1,1 @@
            -Generated file for SomeProject.git
            +Patched file for SomeProject.git
            """
        And a fetched and committed MyProject with the manifest
            """
            manifest:
                version: 0.0
                projects:
                  - name: SomeProject
                    url: some-remote-server/SomeProject.git
                    patch: patches/SomeProject.patch
            """

    Scenario: Patch is updated with new local changes
        Given "SomeProject/README.md" in MyProject is changed and committed with
            """
            Update to patched file for SomeProject.git
            """
        When I run "dfetch update-patch SomeProject" in MyProject
        Then the patch file 'MyProject/patches/SomeProject.patch' is updated
            """
            diff --git a/README.md b/README.md
            index 1e65bd6..925b8c4 100644
            --- a/README.md
            +++ b/README.md
            @@ -1 +1,2 @@
            -Generated file for SomeProject.git
            +Patched file for SomeProject.git
            +Update to patched file for SomeProject.git

            """

    Scenario: Patch is updated with new but not ignored files
        Given files as '*.tmp' are ignored in git in MyProject
        And "SomeProject/IGNORE_ME.tmp" in MyProject is created
        And "SomeProject/NEWFILE.md" in MyProject is created
        And all files in MyProject are committed
        When I run "dfetch update-patch SomeProject" in MyProject
        Then the patch file 'MyProject/patches/SomeProject.patch' is updated
            """
            diff --git a/NEWFILE.md b/NEWFILE.md
            new file mode 100644
            index 0000000..0ee3895
            --- /dev/null
            +++ b/NEWFILE.md
            @@ -0,0 +1 @@
            +Some content
            diff --git a/README.md b/README.md
            index 1e65bd6..38c1a65 100644
            --- a/README.md
            +++ b/README.md
            @@ -1 +1 @@
            -Generated file for SomeProject.git
            +Patched file for SomeProject.git

            """
