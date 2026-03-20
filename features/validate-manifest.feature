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
            Dfetch (0.12.1)
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
            Dfetch (0.12.1)
            Schema validation failed:

                manifest-wrong:
                 ^ (line: 1)

            unexpected key not in schema 'manifest-wrong'
            """

    Scenario: A valid archive manifest with integrity hash is validated
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              projects:
                - name: SomeLib
                  url: https://example.com/SomeLib-1.0.tar.gz
                  vcs: archive
                  integrity:
                    hash: sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855

            """
        When I run "dfetch validate"
        Then the output shows
            """
            Dfetch (0.12.1)
              dfetch.yaml         : valid
            """

    Scenario: A manifest with an invalid integrity hash format is rejected
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              projects:
                - name: SomeLib
                  url: https://example.com/SomeLib-1.0.tar.gz
                  vcs: archive
                  integrity:
                    hash: not-a-valid-hash

            """
        When I run "dfetch validate"
        Then the output shows
            """
            Dfetch (0.12.1)
            Schema validation failed:
                      hash: not-a-valid-hash
                ^ (line: 9)
            found non-matching string
            """

    Scenario: A manifest with duplicate project names
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'
              remotes:
                - name: github-com-dfetch-org
                  url-base: https://github.com/dfetch-org/test-repo
              projects:
                - name: ext/test-repo-rev-only
                - name: ext/test-repo-rev-only
            """
        When I run "dfetch validate"
        Then the output shows
            """
            Dfetch (0.12.1)
            Schema validation failed:
            Duplicate manifest.projects.name value(s): ext/test-repo-rev-only
            """
