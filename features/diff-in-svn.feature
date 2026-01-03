Feature: Diff in svn

    If a project contains issues that need to be fixed, the user can work with the *Dfetch'ed* project as
    any other piece of code within the project. To upstream the changes back to the original project, *Dfetch*
    should allow to generate a patch file.

    Background:
        Given a svn-server "SomeProject"
        And a fetched and committed MySvnProject with the manifest
            """
            manifest:
                version: 0.0
                projects:
                  - name: SomeProject
                    url: some-remote-server/SomeProject
                    vcs: svn
            """

    Scenario: A patch file is generated
        Given "SomeProject/README.md" in MySvnProject is changed, added and committed with
            """
            An important sentence for the README!
            """
        When I run "dfetch diff SomeProject" in MySvnProject
        Then the patch file 'MySvnProject/SomeProject.patch' is generated
            """
            Index: README.md
            ===================================================================
            --- README.md
            +++ README.md
            @@ -1,1 +1,2 @@
             some content
            +An important sentence for the README!
            """

    Scenario: New files are part of the patch
        Given files as '*.tmp' are ignored in 'MySvnProject/SomeProject' in svn
        And "SomeProject/NEWFILE.md" in MySvnProject is changed, added and committed with
            """
            A completely new tracked file.
            """
        And "SomeProject/NEW_UNCOMMITTED_FILE.md" in MySvnProject is created
        And "SomeProject/IGNORE_ME.tmp" in MySvnProject is created
        When I run "dfetch diff SomeProject" in MySvnProject
        Then the patch file 'MySvnProject/SomeProject.patch' is generated
            """
            Index: NEWFILE.md
            ===================================================================
            --- NEWFILE.md
            +++ NEWFILE.md
            @@ -0,0 +1,1 @@
            +A completely new tracked file.
            Index: NEW_UNCOMMITTED_FILE.md
            ===================================================================
            --- /dev/null
            +++ NEW_UNCOMMITTED_FILE.md
            @@ -0,0 +1,1 @@
            +Some content
            """

    Scenario: No change is present
        When I run "dfetch diff SomeProject" in MySvnProject
        Then the output shows
        """
        Dfetch (0.11.0)
          SomeProject         : No diffs found since 1
        """

    Scenario: A patch file is generated on uncommitted changes
        Given "SomeProject/README.md" in MySvnProject is changed with
            """
            An important sentence for the README!
            """
        When I run "dfetch diff SomeProject" in MySvnProject
        Then the patch file 'MySvnProject/SomeProject.patch' is generated
            """
            Index: README.md
            ===================================================================
            --- README.md
            +++ README.md
            @@ -1,1 +1,2 @@
             some content
            +An important sentence for the README!
            """

    Scenario: Metadata is not part of diff
        Given the metadata file ".dfetch_data.yaml" of "MySvnProject/SomeProject" is changed
        When I run "dfetch diff SomeProject" in MySvnProject
        Then the output shows
        """
        Dfetch (0.11.0)
          SomeProject         : No diffs found since 1
        """
