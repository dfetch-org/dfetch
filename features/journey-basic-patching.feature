Feature: Basic patch journey

    The main user journey for patching is:
    - Adding a project to a manifest
    - Fetching the new project and committing it.
    - Changing files in the fetched project.
    - Generating a patch file.
    - Update the project again to verify the patch.
    - Amending the changed project and the patch to version control.

    Below scenario is described in the getting started and should at least work.

    Scenario: Basic patch journey

        Given a local git repo "MyPatchExample" with the manifest
            """
            manifest:
              version: '0.0'

              projects:
                - name: test-repo
                  dst: ext/test-repo
                  tag: v1
                  url: https://github.com/dfetch-org/test-repo
            """
        When I run "dfetch update test-repo" in MyPatchExample
        Then the following projects are fetched
            | path                           |
            | MyPatchExample/ext/test-repo   |
        When all files in MyPatchExample/ext/test-repo are committed
        And "ext/test-repo/my-new-file.md" in MyPatchExample is created
        When I run "dfetch diff test-repo" in MyPatchExample
        Then the patch file 'MyPatchExample/test-repo.patch' is generated
            """
            diff --git a/my-new-file.md b/my-new-file.md
            new file mode 100644
            index 0000000..0ee3895
            --- /dev/null
            +++ my-new-file.md
            @@ -0,0 +1 @@
            +Some content
            """
        When the manifest 'dfetch.yaml' in MyPatchExample is changed to
            """
            manifest:
              version: '0.0'

              projects:
                - name: test-repo
                  dst: ext/test-repo
                  tag: v1
                  url: https://github.com/dfetch-org/test-repo
                  patch: test-repo.patch
            """
        And I run "dfetch update -f test-repo"
        Then the output shows
            """
            Dfetch (0.11.0)
              test-repo           : Fetched v1
              test-repo           : Applied patch "test-repo.patch"
            """
