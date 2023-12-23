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
            Index: SomeProject/README.md
            ===================================================================
            --- SomeProject/README.md	(revision 1)
            +++ SomeProject/README.md	(working copy)
            @@ -1 +1,2 @@
             some content
            +An important sentence for the README!
            """

    Scenario: No change is present
        When I run "dfetch diff SomeProject" in MySvnProject
        Then the output shows
        """
        Dfetch (0.8.0)
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
            Index: SomeProject/README.md
            ===================================================================
            --- SomeProject/README.md	(revision 1)
            +++ SomeProject/README.md	(working copy)
            @@ -1 +1,2 @@
             some content
            +An important sentence for the README!
            """
