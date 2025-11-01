Feature: Filtering file paths before executing a tool

    Projects are dfetched and used in parent projects, users would like to run
    static analysis tools but ignore externally vendored projects. The dfetch filter
    command makes it possible to wrap a cal to another tool and filter out any external files.
    Also it is possible to list all files that are under control of dfetch and this can be used
    to automate various tasks. Paths outside the top-level directory should be excluded to prevent
    any path traversal.

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

    Scenario: Tool receives only managed files
        When I run "git ls-files | dfetch filter echo"
        Then the output shows
            """
            Dfetch (0.10.0)
            ext/test-repo-rev-only: wanted (e1fda19a57b873eb8e6ae37780594cbb77b70f1a), available (e1fda19a57b873eb8e6ae37780594cbb77b70f1a)
            ext/test-rev-and-branch: wanted (main - 8df389d0524863b85f484f15a91c5f2c40aefda1), available (main - e1fda19a57b873eb8e6ae37780594cbb77b70f1a)
            """

#   Scenario: Tool receives only unmanaged files

#   Scenario: Fail on path traversal outside top-level manifest directory
