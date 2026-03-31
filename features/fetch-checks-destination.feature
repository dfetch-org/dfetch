Feature: Fetch checks destinations

    Destinations marked with the 'dst:' attribute can be misused and lead to
    issues in the existing project. For instance path traversal or overwriting
    of other fetched projects. *DFetch* should do some sanity checks on the destinations.

    Scenario: No fetch is done directly into manifest folder
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              projects:
                - name: ext/test-repo-tag
                  url: https://github.com/dfetch-org/test-repo
                  tag: v1
                  dst: .

            """
        When I run "dfetch update"
        Then the output shows
            """
            Dfetch (0.14.0)
              ext/test-repo-tag:
              > Skipping, path "." is not allowed as destination.
            """

    Scenario: Path traversal is not allowed
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              projects:
                - name: ext/test-repo-tag
                  url: https://github.com/dfetch-org/test-repo
                  tag: v1
                  dst: ../../some-higher-folder

            """
        When I run "dfetch update"
        Then the output shows
            """
            Dfetch (0.14.0)
              ext/test-repo-tag:
              > Skipping, path "../../some-higher-folder" is outside manifest directory tree.
            """
