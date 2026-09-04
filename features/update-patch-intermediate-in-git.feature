@update-patch
Feature: Update an intermediate patch in a stack

    When a project carries a stack of several patches, a local change may
    belong to an earlier patch rather than the last one. The ``--patch``
    option lets the user record the change into that patch instead, so the
    rest of the stack keeps its concern-per-patch structure. Later patches
    are rebased on top of the newly recorded one.

    Background:
        Given a git repository "SomeProject.git"
        And the patch file 'MyProject/patches/0001-readme.patch'
            """
            diff --git a/README.md b/README.md
            index 32d9fad..62248b7 100644
            --- a/README.md
            +++ b/README.md
            @@ -1,1 +1,1 @@
            -Generated file for SomeProject.git
            +Patched file for SomeProject.git
            """
        And the patch file 'MyProject/patches/0002-extra-file.patch'
            """
            diff --git a/EXTRA.md b/EXTRA.md
            new file mode 100644
            index 0000000..b3aa595
            --- /dev/null
            +++ b/EXTRA.md
            @@ -0,0 +1 @@
            +Some extra content
            """
        And a fetched and committed MyProject with the manifest
            """
            manifest:
                version: 0.0
                projects:
                  - name: SomeProject
                    url: some-remote-server/SomeProject.git
                    patch:
                      - patches/0001-readme.patch
                      - patches/0002-extra-file.patch
            """

    Scenario: A change is recorded into an intermediate patch by index
        Given "SomeProject/README.md" in MyProject is changed and committed with
            """
            Update to patched file for SomeProject.git
            """
        When I run "dfetch update-patch SomeProject --patch 1" in MyProject
        Then the patch file 'MyProject/patches/0001-readme.patch' is updated
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
        And the patch file 'MyProject/patches/0002-extra-file.patch' is updated
            """
            diff --git a/EXTRA.md b/EXTRA.md
            new file mode 100644
            index 0000000..b3aa595
            --- /dev/null
            +++ b/EXTRA.md
            @@ -0,0 +1 @@
            +Some extra content
            """
        And the patched 'MyProject/SomeProject/README.md' is
            """
            Patched file for SomeProject.git
            Update to patched file for SomeProject.git
            """
        And the patched 'MyProject/SomeProject/EXTRA.md' is
            """
            Some extra content
            """

    Scenario: A change is recorded into an intermediate patch by name
        Given "SomeProject/README.md" in MyProject is changed and committed with
            """
            Update to patched file for SomeProject.git
            """
        When I run "dfetch update-patch SomeProject --patch 0001-readme" in MyProject
        Then the patch file 'MyProject/patches/0001-readme.patch' is updated
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

    Scenario: A change conflicting with a later patch is rejected and the project restored
        Given "SomeProject/EXTRA.md" in MyProject is removed and committed
        When I run "dfetch update-patch SomeProject --patch 1" in MyProject
        Then the patch file 'MyProject/patches/0001-readme.patch' is updated
            """
            diff --git a/README.md b/README.md
            index 32d9fad..62248b7 100644
            --- a/README.md
            +++ b/README.md
            @@ -1,1 +1,1 @@
            -Generated file for SomeProject.git
            +Patched file for SomeProject.git
            """
        And the patched 'MyProject/SomeProject/README.md' is
            """
            Patched file for SomeProject.git
            """
