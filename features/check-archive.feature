@check
Feature: Checking dependencies from an archive

    DFetch can check if archive-based projects are up-to-date.
    For archives without an integrity hash the URL is the version identifier
    so the project is always considered up-to-date once fetched (the URL has
    not changed). For archives with an 'integrity.hash' the hash is the
    version identifier, and dfetch reports whether the locally stored version
    matches the wanted hash.

    Scenario: Archive project without hash is reported as up-to-date after fetch
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
        When I run "dfetch check" in MyProject
        Then the output shows
            """
            Dfetch (0.13.0)
              SomeProject:
              > up-to-date (some-remote-server/SomeProject.tar.gz)
            """

    Scenario: Archive project with correct sha256 hash is reported as up-to-date
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
                  integrity:
                    hash: sha256:<archive-sha256>
            """
        And all projects are updated in MyProject
        When I run "dfetch check" in MyProject
        Then the output shows
            """
            Dfetch (0.13.0)
              SomeProject:
              > up-to-date (sha256:<archive-sha256>)
            """

    Scenario: Archive project that has not been fetched yet is reported
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
        When I run "dfetch check" in MyProject
        Then the output shows
            """
            Dfetch (0.13.0)
              SomeProject:
              > wanted (some-remote-server/SomeProject.tar.gz), available (some-remote-server/SomeProject.tar.gz)
            """

    Scenario: Non-existent archive URL is reported
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'
              projects:
                - name: non-existent-archive
                  url: https://dfetch.invalid/does-not-exist.tar.gz
                  vcs: archive
            """
        When I run "dfetch check"
        Then the output shows
            """
            Dfetch (0.13.0)
              non-existent-archive:
              > wanted (https://dfetch.invalid/does-not-exist.tar.gz), but not available at the upstream.
            """

    Scenario: Archive project with ignore list shows no local changes after fresh fetch
        Given an archive "SomeProject.tar.gz" with the files
            | path              |
            | README.md         |
            | src/main.c        |
            | tests/test_main.c |
        And the manifest 'dfetch.yaml' in MyProject
            """
            manifest:
              version: '0.0'
              projects:
                - name: SomeProject
                  url: some-remote-server/SomeProject.tar.gz
                  vcs: archive
                  ignore:
                    - tests
            """
        And all projects are updated in MyProject
        When I run "dfetch check SomeProject" in MyProject
        Then the output shows
            """
            Dfetch (0.13.0)
              SomeProject:
              > up-to-date (some-remote-server/SomeProject.tar.gz)
            """

    Scenario: Archive with local changes is reported
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
        And "SomeProject/README.md" in MyProject is changed locally
        When I run "dfetch check SomeProject" in MyProject
        Then the output shows
            """
            Dfetch (0.13.0)
              SomeProject:
              > Local changes were detected, please generate a patch using 'dfetch diff SomeProject' and add it to your manifest using 'patch:'. Alternatively overwrite the local changes with 'dfetch update --force SomeProject'
              > up-to-date (some-remote-server/SomeProject.tar.gz)
            """
