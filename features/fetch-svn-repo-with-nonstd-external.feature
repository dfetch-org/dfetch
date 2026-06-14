@update @report
Feature: Fetch projects with non-standard-layout SVN externals

    SVN externals can point to a repository root that has no trunk/branches/tags
    layout.  DFetch should detect and report these with an empty branch value
    (represented internally as a single space) rather than treating them as a
    standard branch.

    Background:
        Given a non-standard svn-server "NonstdLib" with the files
            | path      |
            | README.md |
        And a svn-server "ParentProject" with the files
            | path      |
            | README.md |
        And svn-server "ParentProject" has an external at "nonstd-ext" from non-standard svn-server "NonstdLib"

    Scenario: A project with a non-standard-layout SVN external is fetched and the external is reported
        Given the manifest 'dfetch.yaml' in MyProject
            """
            manifest:
                version: 0.0
                projects:
                    - name: svn-project-with-nonstd-external
                      url: some-remote-server/ParentProject
                      vcs: svn
            """
        When I run "dfetch update" in MyProject
        Then the output shows
            """
            Dfetch (0.14.0)
              svn-project-with-nonstd-external:
              > Found & fetched external "./nonstd-ext" (some-remote-server/NonstdLib @ )
              > Fetched trunk - 2
            """
        And 'MyProject' looks like:
            """
            MyProject/
                dfetch.yaml
                svn-project-with-nonstd-external/
                    .dfetch_data.yaml
                    README.md
                    nonstd-ext/
                        README.md
            """

    Scenario: Non-standard external is shown in the project report with no branch
        Given a fetched and committed MyProject with the manifest
            """
            manifest:
                version: 0.0
                projects:
                    - name: svn-project-with-nonstd-external
                      url: some-remote-server/ParentProject
                      vcs: svn
            """
        When I run "dfetch report" in MyProject
        Then the output shows
            """
            Dfetch (0.14.0)
              svn-project-with-nonstd-external:
              - remote            : <none>
                remote url        : some-remote-server/ParentProject
                branch            : trunk
                tag               : <none>
                last fetch        :
                revision          : 2
                patch             : <none>
                licenses          : <none>

                dependencies      :
                - path            : nonstd-ext
                  url             : some-remote-server/NonstdLib
                  branch          :
                  tag             : <none>
                  revision        : <none>
                  source-type     : svn-external
            """
