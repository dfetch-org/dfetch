Feature: Guard against overwriting in svn

    Accidentally overwriting local changes could lead to introducing regressions.
    To make developers aware of overwriting, store hash after an update and compare
    this with hashes just before an update.

    Background:
        Given a svn-server "SomeProject" with the tag "v1"
        And a fetched and committed MySvnProject with the manifest
            """
            manifest:
                version: 0.0
                projects:
                    - name: SomeProject
                      url: some-remote-server/SomeProject
                      tag: 'v1'
            """
        And a new tag "v2" is added to "SomeProject"
        And "tag: 'v1'" is replaced with "tag: 'v2'" in "MySvnProject/dfetch.yaml"

    Scenario: No update is done when hash is different
        Given "SomeProject/README.md" in MySvnProject is changed locally
        When I run "dfetch update"
        Then the output shows
            """
            Dfetch (0.11.0)
              SomeProject         : skipped - local changes after last update (use --force to overwrite)
            """

    Scenario: Force flag overrides local changes check
        Given "SomeProject/README.md" in MySvnProject is changed locally
        When I run "dfetch update --force"
        Then the output shows
            """
            Dfetch (0.11.0)
              SomeProject         : Fetched v2
            """

    Scenario: Ignored files are overwritten
        Given files as '*.tmp' are ignored in 'MySvnProject/SomeProject' in svn
        And "SomeProject/IGNORE_ME.tmp" in MySvnProject is created
        When I run "dfetch update SomeProject"
        Then the output shows
            """
            Dfetch (0.11.0)
              SomeProject         : Fetched v2
            """
