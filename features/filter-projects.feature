@wip
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
        When I run "dfetch filter"
        Then the output shows
            """
            /some/dir/MyProject/SomeProject
            /some/dir/MyProject/SomeProject/README.md
            /some/dir/MyProject/SomeProject/.dfetch_data.yaml
            """

#   Scenario: Tool receives only unmanaged files

#   Scenario: Fail on path traversal outside top-level manifest directory
