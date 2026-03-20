Feature: Freeze archive dependencies

    For archive projects, 'dfetch freeze' adds a sha256 hash to the manifest
    to pin the exact archive content. This uses the 'hash: sha256:<hex>'
    format, which can be extended to other algorithms in the future.

    Scenario: Archive project is frozen with its sha256 hash
        Given an archive "SomeProject.tar.gz" with the files
            | path      |
            | README.md |
        And the manifest 'dfetch.yaml' in MyProject
            """
            manifest:
              version: '0.0'
              projects:
                - name: SomeProject
                  url: some-remote-server/SomeProject.tar.gz
                  vcs: archive
            """
        And all projects are updated in MyProject
        When I run "dfetch freeze" in MyProject
        Then the manifest 'dfetch.yaml' is replaced with
            """
            manifest:
              version: '0.0'

              projects:
              - name: SomeProject
                url: some-remote-server/SomeProject.tar.gz
                vcs: archive
                hash: sha256:<archive-sha256>

            """

    Scenario: Already frozen archive project is not changed by freeze
        Given an archive "SomeProject.tar.gz" with the files
            | path      |
            | README.md |
        And the manifest 'dfetch.yaml' in MyProject
            """
            manifest:
              version: '0.0'
              projects:
                - name: SomeProject
                  url: some-remote-server/SomeProject.tar.gz
                  vcs: archive
                  hash: sha256:<archive-sha256>
            """
        And all projects are updated in MyProject
        When I run "dfetch freeze" in MyProject
        Then the manifest 'dfetch.yaml' is replaced with
            """
            manifest:
              version: '0.0'

              projects:
              - name: SomeProject
                url: some-remote-server/SomeProject.tar.gz
                vcs: archive
                hash: sha256:<archive-sha256>

            """
