Feature: Formatting a patch for git repositories

    If a project is fetched from a git repository, and changes are made to
    that project, *DFetch* should be able to create a patch file that can be
    applied to the original repository. This way the upstream repository can
    be kept up to date with local changes.

    Scenario: All patch files are formatted
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
                  dst: ext/test-repo-tag
                  patch:
                    - 001-diff.patch
                    - 002-diff.patch
                    - 003-new-file.patch
            """
        And the patch file '001-diff.patch'
            """
            diff --git a/README.md b/README.md
            index 32d9fad..62248b7 100644
            --- a/README.md
            +++ b/README.md
            @@ -1,2 +1,2 @@
             # Test-repo
            -A test repo for testing dfetch.
            +A test repo for testing patch.
            """
        And the patch file '002-diff.patch'
            """
            diff --git a/README.md b/README.md
            index 32d9fad..62248b7 100644
            --- a/README.md
            +++ b/README.md
            @@ -1,2 +1,2 @@
             # Test-repo
            -A test repo for testing patch.
            +A test repo for testing formatting patches.
            """
        And the patch file '003-new-file.patch'
            """
            diff --git a/NEWFILE.md b/NEWFILE.md
            new file mode 100644
            index 0000000..e69de29
            --- /dev/null
            +++ b/NEWFILE.md
            @@ -0,0 +1 @@
            +This is a new file.
            """
        And all projects are updated
        When I run "dfetch format-patch ext/test-repo-tag --output-directory patches"
        Then the patch file 'patches/001-diff.patch' is generated
            """
            From 0000000000000000000000000000000000000000 Mon Sep 17 00:00:00 2001
            From: John Doe <john@dfetch.io>
            Date: Mon, 02 Feb 2026 21:02:42 +0000
            Subject: [PATCH 1/3] Patch for ext/test-repo-tag

            Patch for ext/test-repo-tag

            diff --git a/README.md b/README.md
            index 32d9fad..62248b7 100644
            --- a/README.md
            +++ b/README.md
            @@ -1,2 +1,2 @@
            # Test-repo
            -A test repo for testing dfetch.
            +A test repo for testing patch.

            """
        And the patch file 'patches/002-diff.patch' is generated
            """
            From 0000000000000000000000000000000000000000 Mon Sep 17 00:00:00 2001
            From: John Doe <john@dfetch.io>
            Date: Mon, 02 Feb 2026 21:02:42 +0000
            Subject: [PATCH 2/3] Patch for ext/test-repo-tag

            Patch for ext/test-repo-tag

            diff --git a/README.md b/README.md
            index 32d9fad..62248b7 100644
            --- a/README.md
            +++ b/README.md
            @@ -1,2 +1,2 @@
            # Test-repo
            -A test repo for testing patch.
            +A test repo for testing formatting patches.

            """
        And the patch file 'patches/003-new-file.patch' is generated
            """
            From 0000000000000000000000000000000000000000 Mon Sep 17 00:00:00 2001
            From: John Doe <john@dfetch.io>
            Date: Mon, 02 Feb 2026 21:02:42 +0000
            Subject: [PATCH 3/3] Patch for ext/test-repo-tag

            Patch for ext/test-repo-tag

            diff --git a/NEWFILE.md b/NEWFILE.md
            new file mode 100644
            index 0000000..e69de29
            --- /dev/null
            +++ b/NEWFILE.md
            @@ -0,0 +1,1 @@
            +This is a new file.

            """
