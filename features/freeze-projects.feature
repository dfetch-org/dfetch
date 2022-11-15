Feature: Freeze dependencies

    If a user didn't use a revision or branch in his manifest, he can add these automatically with `dfetch freeze`.
    During development it shouldn't be a problem to track a branch and always fetch the latest changes,
    but when a project becomes more mature, you typically want to freeze the dependencies.

    The same rules apply as for fetching, a tag has precedence over a branch and revision.

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
        When I run "dfetch freeze"
        Then the manifest 'dfetch.yaml' is replaced with
            """
            manifest:
              version: '0.0'

              projects:
              - name: ext/test-repo-tag
                revision: e1fda19a57b873eb8e6ae37780594cbb77b70f1a
                url: https://github.com/dfetch-org/test-repo
                branch: main

            """

    Scenario: SVN projects are specified in the manifest
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              projects:
                - name: ext/test-repo-tag
                  url: https://github.com/dfetch-org/test-repo
                  vcs: svn

            """
        And all projects are updated
        When I run "dfetch freeze"
        Then the manifest 'dfetch.yaml' is replaced with
            """
            manifest:
              version: '0.0'

              projects:
              - name: ext/test-repo-tag
                revision: '5'
                url: https://github.com/dfetch-org/test-repo
                branch: trunk
                vcs: svn

            """
