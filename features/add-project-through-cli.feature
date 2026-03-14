Feature: Add project via CLI

    Dfetch can add projects through the command line without requiring
    manual editing of the manifest file. When a project is added, it is
    appended to the manifest and fetched to disk immediately.

    Scenario Outline: Add a project to the manifest

        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              remotes:
                - name: origin
                  url: https://github.com/example/

              projects:
                - name: ext/core-lib
                  url: https://github.com/example/core-lib
                - name: ext/utils
                  url: https://github.com/example/utils
            """
        When I run "dfetch add <remote_url>"<force_flag>
        Then the manifest 'dfetch.yaml' contains a project
            | name          | url          | branch | dst              | remote |
            | <project>     | <remote_url> | main   | <destination>    | origin |
        And the following projects are fetched
            | path              |
            | <destination>     |

        Examples:
            | remote_url                               | project        | destination        | force_flag |
            | https://github.com/example/new-lib.git   | new-lib        | ext/new-lib        |            |
            | https://github.com/example/tools.git    | tools          | ext/tools          | --force    |
            | https://gitlab.com/other/standalone.git | standalone    |                   |            |

    Scenario: Abort adding a project when confirmation is declined

        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'
              projects: []
            """
        When I run "dfetch add https://github.com/example/demo.git"
        And I answer "n" to the confirmation prompt
        Then the manifest 'dfetch.yaml' is unchanged
        And no projects are fetched

    Scenario: Adding a project with an existing name fails

        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              projects:
                - name: ext/core-lib
                  url: https://github.com/example/core-lib
            """
        When I run "dfetch add https://github.com/example/core-lib.git"
        Then the command fails with an error
        And the manifest 'dfetch.yaml' is unchanged
