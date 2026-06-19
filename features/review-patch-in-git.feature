@review-patch
Feature: Review patches in git

    When working with external projects that have patch files, it is useful to
    be able to inspect what a patch (or a set of patches) contributes to the
    project without permanently modifying the working tree.  *Dfetch* provides
    the ``review-patch`` command for this purpose.

    The command stages the clean upstream source in the git index and applies
    the selected patches to the working tree.  Running ``git diff`` inside the
    project directory then shows exactly what the patches change relative to the
    upstream source.  When the user is done reviewing, the command restores the
    original state: both the working tree and the git index are left clean.

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

    Scenario: All patches are set up for review and state is restored afterwards
        When I run "dfetch review-patch SomeProject" in MyProject
        Then the output shows
            """
            Dfetch (0.14.0)
              SomeProject:
              > Fetched master - f9b88b8259d9a7fb48327bf23beabe40c150d474
              > Applying patch "patches/SomeProject.patch"
                successfully patched 1/1:    b'README.md'
              > stage = upstream, working tree = 1 patch(es) applied — open your editor and run `git diff` to inspect
              > restored
            """
        And the patched 'MyProject/SomeProject/README.md' is
            """
            Patched file for SomeProject.git
            """

    Scenario: Only the first N patches are applied with --count
        When I run "dfetch review-patch --count 0 SomeProject" in MyProject
        Then the output shows
            """
            Dfetch (0.14.0)
              SomeProject:
              > Fetched master - f9b88b8259d9a7fb48327bf23beabe40c150d474
              > stage = upstream, working tree = 0 patch(es) applied — open your editor and run `git diff` to inspect
              > Applying patch "patches/SomeProject.patch"
                successfully patched 1/1:    b'README.md'
              > restored
            """
        And the patched 'MyProject/SomeProject/README.md' is
            """
            Patched file for SomeProject.git
            """

    Scenario: A warning is shown when no patch is defined in the manifest
        Given a fetched and committed MyProject with the manifest
            """
            manifest:
                version: 0.0
                projects:
                  - name: SomeProject
                    url: some-remote-server/SomeProject.git
            """
        When I run "dfetch review-patch SomeProject" in MyProject
        Then the output shows
            """
            Dfetch (0.14.0)
              SomeProject:
              > skipped - there is no patch file, use "dfetch diff" SomeProject to create one
            """

    Scenario: A warning is shown when the project has uncommitted local changes
        Given "SomeProject/README.md" in MyProject is changed locally
        When I run "dfetch review-patch SomeProject" in MyProject
        Then the output shows
            """
            Dfetch (0.14.0)
              SomeProject:
              > skipped - uncommitted changes in SomeProject
            """
