@filter
Feature: Filtering file paths before executing a tool

    Projects are dfetched and used in superprojects. Users would like to run
    static analysis tools or formatters, but skip the externally vendored files.
    The 'dfetch filter' command lists the paths that dfetch manages, filters a
    piped list of paths, or wraps a call to another tool with the filtered paths.
    Paths outside the directory of the manifest are always dropped to prevent
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

    Scenario: All dfetched paths are listed
        When I run "dfetch filter" in MyProject
        Then stdout shows
            """
            SomeProject
            SomeProject/.dfetch_data.yaml
            SomeProject/README.md
            """

    Scenario: All non-dfetched paths are listed
        When I run "dfetch filter --not-dfetched" in MyProject
        Then stdout shows
            """
            dfetch.yaml
            """

    Scenario: Piped paths are filtered to dfetched paths only
        When the following is piped through "dfetch filter" in MyProject
            """
            dfetch.yaml
            SomeProject/README.md
            """
        Then stdout shows
            """
            SomeProject/README.md
            """

    Scenario: Piped paths are filtered to non-dfetched paths only
        When the following is piped through "dfetch filter --not-dfetched" in MyProject
            """
            dfetch.yaml
            SomeProject/README.md
            """
        Then stdout shows
            """
            dfetch.yaml
            """

    Scenario: Paths outside the manifest directory are dropped
        Given "outside.txt" in . is created
        When the following is piped through "dfetch filter" in MyProject
            """
            ../outside.txt
            SomeProject/README.md
            """
        Then stdout shows
            """
            SomeProject/README.md
            """

    Scenario: A wrapped tool is called with the filtered paths
        When I run "dfetch filter git status --short" in MyProject
        Then the command succeeds

    Scenario: A wrapped tool that is not available fails
        When I run "dfetch filter some-nonexistent-tool" in MyProject
        Then the command fails with "some-nonexistent-tool not available on system, please install"
