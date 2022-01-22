Feature: Force fetching dependencies

    The main functionality of *DFetch* is fetching remote dependencies.
    *Dfetch* will keep metadata about the fetched project locally to prevent re-fetching unchanged projects
    or replacing locally changed projects. Sometimes you as a user would like to fetch no-matter-what.
    For instance, the metadata may be invalid or the local version is already the same.

    Scenario: Version check ignored when force flag is given
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              projects:
                - name: ext/test-repo-tag
                  url: https://github.com/dfetch-org/test-repo
                  tag: v1

            """
        And all projects are updated
        When I run "dfetch update --force"
        Then the output shows
            """
            Dfetch (0.5.1)
              ext/test-repo-tag   : Fetched v1
            """

    Scenario: Invalid metadata is ignored
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              projects:
                - name: ext/test-repo-tag
                  url: https://github.com/dfetch-org/test-repo
                  tag: v1

            """
        And all projects are updated
        And the metadata file ".dfetch_data.yaml" of "ext/test-repo-tag" is corrupt
        When I run "dfetch update --force"
        Then the output shows
            """
            Dfetch (0.5.1)
              ext/test-repo-tag   : Fetched v1
            """
