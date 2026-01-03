Feature: Diff in git

    If a project contains issues that need to be fixed, the user can work with the *Dfetch'ed* project as
    any other piece of code within the project. To upstream the changes back to the original project, *Dfetch*
    should allow to generate a patch file.

    Background:
        Given a git repository "SomeProject.git"
        And a fetched and committed MyProject with the manifest
            """
            manifest:
                version: 0.0
                projects:
                  - name: SomeProject
                    url: some-remote-server/SomeProject.git
            """

    Scenario: A patch file is generated
        Given "SomeProject/README.md" in MyProject is changed and committed with
            """
            An important sentence for the README!
            """
        When I run "dfetch diff SomeProject"
        Then the patch file 'MyProject/SomeProject.patch' is generated
            """
            diff --git a/README.md b/README.md
            index 1e65bd6..faa3b21 100644
            --- a/README.md
            +++ b/README.md
            @@ -1 +1,2 @@
            Generated file for SomeProject.git
            +An important sentence for the README!
            """

    Scenario: New files are part of the patch
        Given files as '*.tmp' are ignored in git in MyProject
        And "SomeProject/NEWFILE.md" in MyProject is created and committed with
            """
            A completely new tracked file.
            """
        And "SomeProject/NEW_UNCOMMITTED_FILE.md" in MyProject is created
        And "SomeProject/IGNORE_ME.tmp" in MyProject is created
        When I run "dfetch diff SomeProject"
        Then the patch file 'MyProject/SomeProject.patch' is generated
            """
            diff --git a/NEWFILE.md b/NEWFILE.md
            new file mode 100644
            index 0000000..a2d8605
            --- /dev/null
            +++ b/NEWFILE.md
            @@ -0,0 +1 @@
            +A completely new tracked file.

            diff --git a/NEW_UNCOMMITTED_FILE.md b/NEW_UNCOMMITTED_FILE.md
            new file mode 100644
            index 0000000..0ee3895
            --- /dev/null
            +++ NEW_UNCOMMITTED_FILE.md
            @@ -0,0 +1 @@
            +Some content

            """

    Scenario: No change is present
        When I run "dfetch diff SomeProject"
        Then the output shows
        """
        Dfetch (0.11.0)
          SomeProject         : No diffs found since 59efb91396fd369eb113b43382783294dc8ed6d2
        """

    Scenario: Diff is generated on uncommitted changes
        Given "SomeProject/README.md" in MyProject is changed with
            """
            An important sentence for the README!
            """
        When I run "dfetch diff SomeProject"
        Then the patch file 'MyProject/SomeProject.patch' is generated
            """
            diff --git a/README.md b/README.md
            index 1e65bd6..faa3b21 100644
            --- a/README.md
            +++ b/README.md
            @@ -1 +1,2 @@
            Generated file for SomeProject.git
            +An important sentence for the README!
            """

    Scenario: Metadata is not part of diff
        Given the metadata file ".dfetch_data.yaml" of "MyProject/SomeProject" is changed
        When I run "dfetch diff SomeProject"
        Then the output shows
        """
        Dfetch (0.11.0)
          SomeProject         : No diffs found since 59efb91396fd369eb113b43382783294dc8ed6d2
        """
