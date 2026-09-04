@update-patch
Feature: An intermediate patch conflict must never be silently discarded

    Reversing the patches above the target has to be exact. If a later
    patch's context no longer matches, that must be reported as a
    conflict - never resolved with fuzzy matching, which would silently
    drop part of the user's change instead of recording it.

    Background:
        Given a git repository "SomeProject.git"
        And the patch file 'MyProject/patches/0001-first-line.patch'
            """
            diff --git a/README.md b/README.md
            index 32d9fad..62248b7 100644
            --- a/README.md
            +++ b/README.md
            @@ -1,1 +1,1 @@
            -Generated file for SomeProject.git
            +Patched file for SomeProject.git
            """
        And the patch file 'MyProject/patches/0002-first-line-again.patch'
            """
            diff --git a/README.md b/README.md
            index 62248b7..a1b2c3d 100644
            --- a/README.md
            +++ b/README.md
            @@ -1,1 +1,1 @@
            -Patched file for SomeProject.git
            +Patched file for SomeProject.git, v2
            """
        And a fetched and committed MyProject with the manifest
            """
            manifest:
                version: 0.0
                projects:
                  - name: SomeProject
                    url: some-remote-server/SomeProject.git
                    patch:
                      - patches/0001-first-line.patch
                      - patches/0002-first-line-again.patch
            """

    Scenario: A direct edit that conflicts with a later patch is rejected, not fuzzily merged
        Given "Patched file for SomeProject.git, v2" is replaced with "Conflicting direct edit" in "MyProject/SomeProject/README.md"
        And all files in MyProject are committed
        When I run "dfetch update-patch SomeProject --patch 1" in MyProject
        Then the patch file 'MyProject/patches/0001-first-line.patch' is updated
            """
            diff --git a/README.md b/README.md
            index 32d9fad..62248b7 100644
            --- a/README.md
            +++ b/README.md
            @@ -1,1 +1,1 @@
            -Generated file for SomeProject.git
            +Patched file for SomeProject.git
            """
        And the patch file 'MyProject/patches/0002-first-line-again.patch' is updated
            """
            diff --git a/README.md b/README.md
            index 62248b7..a1b2c3d 100644
            --- a/README.md
            +++ b/README.md
            @@ -1,1 +1,1 @@
            -Patched file for SomeProject.git
            +Patched file for SomeProject.git, v2
            """
        And the patched 'MyProject/SomeProject/README.md' is
            """
            Conflicting direct edit
            """
