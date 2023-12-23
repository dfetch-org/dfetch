Feature: Validate a manifest

    *DFetch* can check if the manifest is valid.

    Scenario: A valid manifest is provided
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              remotes:
                - name: github-com-dfetch-org
                  url-base: https://github.com/dfetch-org/test-repo

              projects:
                - name: ext/test-repo-rev-only
                  revision: e1fda19a57b873eb8e6ae37780594cbb77b70f1a

            """
        When I run "dfetch validate"
        Then the output shows
            """
            Dfetch (0.8.0)
              dfetch.yaml         : valid
            """

    Scenario: An invalid manifest is provided
        Given the manifest 'dfetch.yaml'
            """
            manifest-wrong:
              version: '0.0'

              remotes:
                - name: github-com-dfetch-org
                  url-base: https://github.com/dfetch-org/test-repo

              projects:
                - name: ext/test-repo-rev-only
                  revision: e1fda19a57b873eb8e6ae37780594cbb77b70f1a

            """
        When I run "dfetch validate"
        Then the output shows
            """
            Dfetch (0.8.0)
            Schema validation failed:
             - Cannot find required key 'manifest'. Path: ''.
             - Key 'manifest-wrong' was not defined. Path: ''.
            """
