Feature: Guard against overwriting

    Accidentally overwriting local changes could lead to introducing regressions.
    To make developers aware of overwriting, store hash after an update and compare
    this with hashes just before an update.

    Scenario: No update is done when hash is different
        Given MyProject with dependency "SomeProject.git" that must be updated
        When "SomeProject/README.md" in MyProject is changed locally
        And I run "dfetch update"
        Then the output shows
            """
            Dfetch (0.8.0)
              SomeProject         : skipped - local changes after last update (use --force to overwrite)
            """

    Scenario: Force flag overrides local changes check
        Given MyProject with dependency "SomeProject.git" that must be updated
        When "SomeProject/README.md" in MyProject is changed locally
        And I run "dfetch update --force"
        Then the output shows
            """
            Dfetch (0.8.0)
              SomeProject         : Fetched v2
            """
