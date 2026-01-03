Feature: List dependencies

    The report command lists the current state of the projects. It will aggregate the metadata for each project
    and list it. This includes metadata from the manifest file and the metadata file (.dfetch_data.yaml)

    Scenario: Git projects are specified in the manifest
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              remotes:
                - name: github-com-dfetch-org
                  url-base: https://github.com/dfetch-org/test-repo

              projects:
                - name: ext/test-repo-tag
                  url: https://github.com/dfetch-org/test-repo
                  branch: main

                - name: ext/test-rev-and-branch
                  tag: v1
                  dst: ext/test-rev-and-branch

            """
        And all projects are updated
        When I run "dfetch report"
        Then the output shows
            """
            Dfetch (0.11.0)
              project             : ext/test-repo-tag
                  remote          : <none>
                  remote url      : https://github.com/dfetch-org/test-repo
                  branch          : main
                  tag             : <none>
                  last fetch      : 02/07/2021, 20:25:56
                  revision        : e1fda19a57b873eb8e6ae37780594cbb77b70f1a
                  patch           : <none>
                  licenses        : MIT License
              project             : ext/test-rev-and-branch
                  remote          : github-com-dfetch-org
                  remote url      : https://github.com/dfetch-org/test-repo
                  branch          : main
                  tag             : v1
                  last fetch      : 02/07/2021, 20:25:56
                  revision        : <none>
                  patch           : <none>
                  licenses        : MIT License
            """

    @remote-svn
    Scenario: SVN projects are specified in the manifest
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              projects:
                - name: cutter-svn-tag
                  url: svn://svn.code.sf.net/p/cutter/svn/cutter
                  tag: 1.1.7
                  vcs: svn
                  src: acmacros

            """
        And all projects are updated
        When I run "dfetch report"
        Then the output shows
            """
            Dfetch (0.11.0)
              project             : cutter-svn-tag
                  remote          : <none>
                  remote url      : svn://svn.code.sf.net/p/cutter/svn/cutter
                  branch          : <none>
                  tag             : 1.1.7
                  last fetch      : 29/12/2024, 20:09:21
                  revision        : 4007
                  patch           : <none>
                  licenses        : <none>
            """

    Scenario: Git repo with applied patch
        Given MyProject with applied patch 'diff.patch'
        When I run "dfetch report"
        Then the output shows
            """
            Dfetch (0.11.0)
              project             : ext/test-repo-tag
                  remote          : github-com-dfetch-org
                  remote url      : https://github.com/dfetch-org/test-repo
                  branch          : main
                  tag             : v2.0
                  last fetch      : 02/07/2021, 20:25:56
                  revision        : <none>
                  patch           : diff.patch
                  licenses        : MIT License
            """
