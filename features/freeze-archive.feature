Feature: Freeze archive dependencies

    For archive projects, 'dfetch freeze' adds a sha256 hash to the manifest
    to pin the exact archive content. This uses the 'integrity.hash: sha256:<hex>'
    format, which can be extended to other algorithms or signature fields in
    the future.

    Archives that already have an integrity hash in the manifest are left unchanged.

    Scenario: Archive project is frozen with its sha256 hash
        Given an archive "SomeProject.tar.gz" with the files
            | path      |
            | README.md |
        And the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              projects:
                - name: SomeProject
                  url: some-remote-server/SomeProject.tar.gz
                  vcs: archive
            """
        And all projects are updated
        When I run "dfetch freeze"
        Then the manifest 'dfetch.yaml' is replaced with
            """
            manifest:
              version: '0.0'

              projects:
              - name: SomeProject
                url: some-remote-server/SomeProject.tar.gz
                vcs: archive
                integrity:
                  hash: sha256:<archive-sha256>

            """

    Scenario: Already frozen archive project is not changed by freeze
        Given an archive "SomeProject.tar.gz" with the files
            | path      |
            | README.md |
        And the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'
              projects:
                - name: SomeProject
                  url: some-remote-server/SomeProject.tar.gz
                  vcs: archive
                  integrity:
                    hash: sha256:<archive-sha256>
            """
        And all projects are updated
        When I run "dfetch freeze"
        Then the manifest 'dfetch.yaml' is replaced with
            """
            manifest:
              version: '0.0'
              projects:
              - name: SomeProject
                url: some-remote-server/SomeProject.tar.gz
                vcs: archive
                integrity:
                  hash: sha256:<archive-sha256>

            """
