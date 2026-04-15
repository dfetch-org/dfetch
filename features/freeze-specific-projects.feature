@freeze
Feature: Freeze specific projects

    *DFetch* can freeze specific projects by name, leaving other projects untouched.
    This is useful when only some dependencies need to be pinned.

    Scenario: Single project is frozen while another is skipped
        Given the manifest 'dfetch.yaml'
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
        And all projects are updated
        When I run "dfetch freeze ext/test-repo-tag"
        Then the manifest 'dfetch.yaml' is replaced with
            """
            manifest:
              version: '0.0'

              projects:
              - name: ext/test-repo-tag
                url: https://github.com/dfetch-org/test-repo
                revision: e1fda19a57b873eb8e6ae37780594cbb77b70f1a
                branch: main

              - name: ext/test-repo-tag2
                url: https://github.com/dfetch-org/test-repo
                branch: main

            """
