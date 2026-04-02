Feature: Freeze manifest in-place inside a version-controlled superproject

    When the manifest lives inside a git or SVN superproject, ``dfetch freeze``
    edits the manifest file **in-place** instead of creating a ``.backup`` copy.
    Comments, blank lines, and the original indentation are all preserved.

    Scenario: Git projects are frozen in-place preserving layout
        Given a local git repo "superproject" with the manifest
            """
            manifest:
              version: '0.0'

              projects:
                - name: ext/test-repo-tag
                  url: https://github.com/dfetch-org/test-repo
                  branch: main

            """
        And all projects are updated in superproject
        When I run "dfetch freeze" in superproject
        Then the manifest 'dfetch.yaml' in superproject is replaced with
            """
            manifest:
              version: '0.0'

              projects:
                - name: ext/test-repo-tag
                  revision: e1fda19a57b873eb8e6ae37780594cbb77b70f1a
                  url: https://github.com/dfetch-org/test-repo
                  branch: main

            """
        And no file 'dfetch.yaml.backup' exists in superproject

    Scenario: Only selected project is frozen in-place
        Given a local git repo "superproject2" with the manifest
            """
            manifest:
              version: '0.0'

              projects:
                - name: ext/test-repo-tag
                  url: https://github.com/dfetch-org/test-repo
                  branch: main

                - name: ext/test-repo-tag2
                  url: https://github.com/dfetch-org/test-repo
                  branch: main

            """
        And all projects are updated in superproject2
        When I run "dfetch freeze ext/test-repo-tag" in superproject2
        Then the manifest 'dfetch.yaml' in superproject2 is replaced with
            """
            manifest:
              version: '0.0'

              projects:
                - name: ext/test-repo-tag
                  revision: e1fda19a57b873eb8e6ae37780594cbb77b70f1a
                  url: https://github.com/dfetch-org/test-repo
                  branch: main

                - name: ext/test-repo-tag2
                  url: https://github.com/dfetch-org/test-repo
                  branch: main

            """
