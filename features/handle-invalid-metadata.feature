Feature: Handle invalid metadata files

    *Dfetch* will keep metadata about the fetched project locally to prevent re-fetching unchanged projects
    or replacing locally changed projects. Sometimes the metadata file will become incorrect and this should not lead
    to unpredictable behavior in *DFetch*.
    For instance, the metadata may be invalid

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
        When I run "dfetch update"
        Then the output shows
            """
            Dfetch (0.8.0)
            ext/test-repo-tag/.dfetch_data.yaml is an invalid metadata file, not checking on disk version!
            ext/test-repo-tag/.dfetch_data.yaml is an invalid metadata file, not checking local hash!
              ext/test-repo-tag   : Fetched v1
            """
