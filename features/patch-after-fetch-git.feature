Feature: Patch after fetching from git repo

    Sometimes a patch needs to be applied after fetching. *DFetch* makes it
    possible to specify a patch file.

    @wip
    Scenario: A patch file is applied after fetching
        Given the manifest 'dfetch.yaml'
            """
            manifest:
                version: '0.0'

                remotes:
                - name: github-com-dfetch-org
                    url-base: https://github.com/dfetch-org/test-repo

                projects:
                - name: ext/test-repo-tag-v1
                    tag: v1
                    dst: ext/test-repo-tag-v1
                    patch: diff.patch
            """
        And the patch file 'diff.patch'
            """
            From f06bb9d817b7dbb3945f55bd9974b5e71c3f84ae Mon Sep 17 00:00:00 2001
            From: Jens Geudens <jensgeudens@hotmail.com>
            Date: Fri, 21 May 2021 19:52:59 +0200
            Subject: [PATCH] Test change for patch

            ---
            README.md | 2 +-
            1 file changed, 1 insertion(+), 1 deletion(-)

            diff --git a/README.md b/README.md
            index 32d9fad..62248b7 100644
            --- a/README.md
            +++ b/README.md
            @@ -1,2 +1,2 @@
            # Test-repo
            -A test repo for testing dfetch.
            +A test repo for testing patch.
            -- 
            2.27.0
            """
        When I run "dfetch update"
        Then the resulting file after patching should be 'README.md'
            """
            # Test-repo
            A test repo for testing patch.
            """