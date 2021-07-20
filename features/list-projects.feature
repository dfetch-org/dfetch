Feature: List dependencies

    The list command lists the current state of the projects. It will aggregate the metadata for each project
    and list it. This includes metadata from the manifest file and the metadata file (.dfetch_data.yaml)

    Scenario: Git projects are specified in the manifest
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              projects:
                - name: ext/test-repo-tag
                  url: https://github.com/dfetch-org/test-repo
                  branch: main

            """
        And all projects are updated
        When I run "dfetch list"
        Then the output shows
            """
            Dfetch (0.2.0)
              project             : ext/test-repo-tag
                  remote          : <none>
                  remote url      : https://github.com/dfetch-org/test-repo
                  branch          : main
                  tag             : <none>
                  last fetch      : 02/07/2021, 20:25:56
                  revision        : e1fda19a57b873eb8e6ae37780594cbb77b70f1a
                  patch           : <none>
            """

    Scenario: SVN projects are specified in the manifest
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              projects:
                - name: ext/test-repo-tag
                  url: https://github.com/dfetch-org/test-repo
                  tag: v2.0
                  vcs: svn

            """
        And all projects are updated
        When I run "dfetch list"
        Then the output shows
            """
            Dfetch (0.2.0)
              project             : ext/test-repo-tag
                  remote          : <none>
                  remote url      : https://github.com/dfetch-org/test-repo
                  branch          : <none>
                  tag             : v2.0
                  last fetch      : 02/07/2021, 20:25:56
                  revision        : 4
                  patch           : <none>
            """
