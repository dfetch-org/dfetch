Feature: Guard against overwriting in git

    Accidentally overwriting local changes could lead to introducing regressions.
    To make developers aware of overwriting, store hash after an update and compare
    this with hashes just before an update.

    Background:
        Given a git repository "SomeProject.git"
        And a fetched and committed MyProject with the manifest
            """
            manifest:
                version: 0.0
                projects:
                  - name: SomeProject
                    url: some-remote-server/SomeProject.git
                    tag: v1
            """
        And a new tag "v2" is added to git-repository "SomeProject.git"
        And "tag: v1" is replaced with "tag: v2" in "MyProject/dfetch.yaml"

    Scenario: No update is done when hash is different
        Given "SomeProject/README.md" in MyProject is changed locally
        When I run "dfetch update"
        Then the output shows
            """
            Dfetch (0.11.0)
              SomeProject         : skipped - local changes after last update (use --force to overwrite)
            """

    Scenario: Force flag overrides local changes check
        Given "SomeProject/README.md" in MyProject is changed locally
        When I run "dfetch update --force"
        Then the output shows
            """
            Dfetch (0.11.0)
              SomeProject         : Fetched v2
            """

    Scenario: Ignored files are overwritten
        Given files as '*.tmp' are ignored in git in MyProject
        And "SomeProject/IGNORE_ME.tmp" in MyProject is created
        When I run "dfetch update SomeProject"
        Then the output shows
            """
            Dfetch (0.11.0)
              SomeProject         : Fetched v2
            """
