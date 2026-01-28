Feature: Patch after fetching from git repo

    Sometimes a patch needs to be applied after fetching. *DFetch* makes it
    possible to specify a patch file.

    Scenario: A patch file is applied after fetching
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
                  patch: diff.patch
            """
        And the patch file 'diff.patch'
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
        When I run "dfetch update"
        Then the patched 'ext/test-repo-tag/README.md' is
            """
            # Test-repo
            A test repo for testing patch.
            """

    Scenario: Applying patch file fails
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
                  patch: diff.patch
            """
        And the patch file 'diff.patch'
            """
            diff --git a/README.md b/README1.md
            index 32d9fad..62248b7 100644
            --- a/README1.md
            +++ b/README1.md
            @@ -1,2 +1,2 @@
             # Test-repo
            -A test repo for testing dfetch.
            +A test repo for testing patch.
            """
        When I run "dfetch update"
        Then the output shows
            """
            Dfetch (0.11.0)
              ext/test-repo-tag:
              > Fetched v2.0
              > Applying patch "diff.patch"
                source/target file does not exist:
                  --- b'README1.md'
                  +++ b'README1.md'
            Applying patch "diff.patch" failed
            """

    Scenario: Multiple patch files are applied after fetching
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
            index 62248b7..32d9fad 100644
            --- a/README.md
            +++ b/README.md
            @@ -1,2 +1,2 @@
             # Test-repo
            -A test repo for testing patch.
            +A test repo for testing dfetch.
            """
        When I run "dfetch update"
        Then the patched 'ext/test-repo-tag/README.md' is
            """
            # Test-repo
            A test repo for testing dfetch.
            """
        And the output shows
            """
            Dfetch (0.11.0)
              ext/test-repo-tag:
              > Fetched v2.0
              > Applying patch "001-diff.patch"
                successfully patched 1/1:    b'README.md'
              > Applying patch "002-diff.patch"
                successfully patched 1/1:    b'README.md'
            """

    Scenario: Fallback to other file encodings if patch file is not UTF-8 encoded
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
                  patch: diff.patch
            """
        And the patch file 'diff.patch' with 'UTF-16' encoding
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
        When I run "dfetch update"
        Then the patched 'ext/test-repo-tag/README.md' is
            """
            # Test-repo
            A test repo for testing patch.
            """
        And the output shows
            """
            Dfetch (0.11.0)
              ext/test-repo-tag:
              > Fetched v2.0
              > Applying patch "diff.patch"
                error: no patch data found!
                successfully patched 1/1:    b'README.md'
              > After retrying found that patch-file "diff.patch" is not UTF-8 encoded, consider saving it with UTF-8 encoding.
            """

    Scenario: Patch files are outside manifest dir
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
                  patch: ../diff.patch
            """
        When I run "dfetch update"
        Then the output shows
            """
            Dfetch (0.11.0)
              ext/test-repo-tag:
              > Fetched v2.0
              > Skipping patch "../diff.patch" which is outside /some/path.
            """
