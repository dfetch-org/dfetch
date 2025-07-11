Feature: Remove a project from the manifest

  Scenario: Remove an existing project
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
    When I run "dfetch remove ext/test-repo-tag"
    Then the manifest 'dfetch.yaml' is replaced with
            """
            manifest:
              version: '0.0'

              projects: []
            """     
    And the directory 'ext/test-repo-tag' should be removed from disk
    And the output shows
            """
            Dfetch (0.10.0)
              ext/test-repo-tag: removed
            """
        
