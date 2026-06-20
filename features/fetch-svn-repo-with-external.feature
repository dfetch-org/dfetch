@update @report
Feature: Fetch projects with nested SVN dependencies

    When fetching an SVN project that defines svn:externals,
    the exported content already includes the external directories.
    DFetch should detect and report these externals so they are
    visible in the project report, mirroring the behaviour for
    Git submodules.

    Background:
        Given a svn-server "ExternalLib" with the files
            | path      |
            | README.md |
        And a svn-server "ParentProject" with the files
            | path      |
            | README.md |
        And svn-server "ParentProject" has an external at "ext" from svn-server "ExternalLib"

    Scenario: A project with an SVN external is fetched and the external is reported
        Given the manifest 'dfetch.yaml' in MyProject
            """
            manifest:
                version: 0.0
                projects:
                    - name: svn-project-with-external
                      url: some-remote-server/ParentProject
                      vcs: svn
            """
        When I run "dfetch update" in MyProject
        Then the output shows
            """
            Dfetch (0.14.1)
              svn-project-with-external:
              > Found & fetched external "./ext" (some-remote-server/ExternalLib @ trunk)
              > Fetched trunk - 2
            """
        And 'MyProject' looks like:
            """
            MyProject/
                dfetch.yaml
                svn-project-with-external/
                    .dfetch_data.yaml
                    README.md
                    ext/
                        README.md
            """

    Scenario: External changes are reported in the project report
        Given a fetched and committed MyProject with the manifest
            """
            manifest:
                version: 0.0
                projects:
                    - name: svn-project-with-external
                      url: some-remote-server/ParentProject
                      vcs: svn
            """
        When I run "dfetch report" in MyProject
        Then the output shows
            """
            Dfetch (0.14.1)
              svn-project-with-external:
              - remote            : <none>
                remote url        : some-remote-server/ParentProject
                branch            : trunk
                tag               : <none>
                last fetch        :
                revision          : 2
                patch             : <none>
                licenses          : <none>

                dependencies      :
                - path            : ext
                  url             : some-remote-server/ExternalLib
                  branch          : <none>
                  tag             : <none>
                  revision        : <none>
                  source-type     : svn-external
            """
