Feature: Basic usage journey

    The main user journey is:
    - Creating a manifest.
    - Fetching all projects in manifest.
    - Checking for new updates
    - Updating manifest due to changes.
    - Fetching new projects.

    Below scenario is described in the getting started and should at least work.

    Scenario: Basic user journey

        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              projects:
                - name: ext/test-repo-tag
                  tag: v1
                  url: https://github.com/dfetch-org/test-repo
            """
        When I run "dfetch update"
        Then the following projects are fetched
            | path                    |
            | ext/test-repo-tag       |
        When I run "dfetch check"
        Then the output shows
            """
            Dfetch (0.8.0)
              ext/test-repo-tag   : wanted & current (v1), available (v2.0)
            """
        When the manifest 'dfetch.yaml' is changed to
            """
            manifest:
              version: '0.0'

              projects:
                - name: ext/test-repo-tag
                  url: https://github.com/dfetch-org/test-repo
                  tag: v2.0
            """
        And I run "dfetch update"
        Then the following projects are fetched
            | path                    |
            | ext/test-repo-tag       |
