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
            Dfetch (0.13.0)
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
            Dfetch (0.13.0)
            Schema validation failed:

                manifest-wrong:
                 ^ (line: 1)

            unexpected key not in schema 'manifest-wrong'
            """

    Scenario: A valid archive manifest with integrity hashes is validated
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              projects:
                - name: SomeLib-sha256
                  url: https://example.com/SomeLib-1.0.tar.gz
                  vcs: archive
                  integrity:
                    hash: sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855

                - name: SomeLib-sha384
                  url: https://example.com/SomeLib-2.0.tar.gz
                  vcs: archive
                  integrity:
                    hash: sha384:38b060a751ac96384cd9327eb1b1e36a21fdb71114be07434c0cc7bf63f6e1da274edebfe76f65fbd51ad2f14898b95b

                - name: SomeLib-sha512
                  url: https://example.com/SomeLib-3.0.tar.gz
                  vcs: archive
                  integrity:
                    hash: sha512:cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce47d0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e

            """
        When I run "dfetch validate"
        Then the output shows
            """
            Dfetch (0.13.0)
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
            Dfetch (0.13.0)
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
            Dfetch (0.13.0)
            Schema validation failed:
            Duplicate manifest.projects.name value(s): ext/test-repo-rev-only
            """
