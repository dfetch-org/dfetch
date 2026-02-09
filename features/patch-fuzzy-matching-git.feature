Feature: Patch application tolerates small upstream changes

    If an upstream git repository changes slightly after a patch was created,
    the patch should still apply successfully using fuzzy matching, as long as
    the changes are compatible.

    Background:
        Given a git repository "SomeProject.git"
        And the patch file 'SomeProject.patch' in MyProject
            """
            diff --git a/README.md b/README.md
            index 1e65bd6..faa3b21 100644
            --- a/README.md
            +++ b/README.md
            @@ -1 +1,2 @@
             Generated file for SomeProject.git
            +An important sentence for the README!
            """
        And a fetched and committed MyProject with the manifest
            """
            manifest:
                version: 0.0
                projects:
                  - name: SomeProject
                    url: some-remote-server/SomeProject.git
                    patch: SomeProject.patch
            """

    Scenario: Patch applies when upstream adds extra lines
        Given "README.md" in git-repository "SomeProject.git" is changed to:
            """
            Generated file for SomeProject.git
            Additional upstream line.
            """
        When I run "dfetch update"
        Then the patched 'MyProject/SomeProject/README.md' is
            """
            Generated file for SomeProject.git
            An important sentence for the README!
            Additional upstream line.
            """

    Scenario: Patch applies when context lines have changed
        Given "README.md" in git-repository "SomeProject.git" is changed to:
            """
            Generated file for SomeProject
            This repository is used for testing.
            """
        And the patch file 'SomeProject.patch' in SomeProject
            """
            diff --git a/README.md b/README.md
            index 1e65bd6..faa3b21 100644
            --- a/README.md
            +++ b/README.md
            @@ -1 +1,2 @@
             Generated file for SomeProject.git
            +An important sentence for the README!
            """
        When I run "dfetch update"
        Then the output shows
            """
            Dfetch (0.11.0)
              SomeProject:
              > Fetched master - f47d80c35e14dfa4f9c9c30c9865cbf0f8d50933
              > Applying patch "SomeProject.patch"
                file 1/1:    b'README.md'
                 hunk no.1 doesn't match source file at line 1
                  expected: b'Generated file for SomeProject.git'
                  actual  : b'Generated file for SomeProject'
                successfully patched 1/1:    b'README.md'
            """
        And the patched 'MyProject/SomeProject/README.md' is
            """
            Generated file for SomeProject
            An important sentence for the README!
            This repository is used for testing.
            """
