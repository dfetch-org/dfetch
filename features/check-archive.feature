Feature: Checking dependencies from an archive

    DFetch can check if archive-based projects are up-to-date.
    For archives without a hash, the URL is used as the version identifier.
    For archives with a 'hash:' field, the hash is verified against the
    downloaded archive to determine if the content matches.

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
            Dfetch (0.12.1)
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
                  hash: sha256:<archive-sha256>
            """
        And all projects are updated in MyProject
        When I run "dfetch check" in MyProject
        Then the output shows
            """
            Dfetch (0.12.1)
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
            Dfetch (0.12.1)
              SomeProject:
              > wanted (some-remote-server/SomeProject.tar.gz), but never fetched!
            """

    Scenario: Non-existent archive URL is reported
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'
              projects:
                - name: non-existent-archive
                  url: https://example.com/does-not-exist.tar.gz
                  vcs: archive
            """
        When I run "dfetch check"
        Then the output shows
            """
            Dfetch (0.12.1)
              non-existent-archive:
              > 'https://example.com/does-not-exist.tar.gz' is not a valid URL or unreachable
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
            Dfetch (0.12.1)
              SomeProject:
              > Local changes were detected, please generate a patch using 'dfetch diff SomeProject' and add it to your manifest using 'patch:'. Alternatively overwrite the local changes with 'dfetch update --force SomeProject'
              > up-to-date (some-remote-server/SomeProject.tar.gz)
            """
