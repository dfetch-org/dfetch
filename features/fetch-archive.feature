Feature: Fetching dependencies from an archive (tar/zip)

    Some projects are distributed as tar or zip archives, for example as
    GitHub release assets or on internal artifact servers. DFetch supports
    fetching these archives using the 'archive' vcs type. Optionally, an
    'integrity:' block with a 'hash:' sub-field can be specified for
    cryptographic integrity verification.

    Scenario: Tar.gz archive project is fetched
        Given an archive "SomeProject.tar.gz" with the files
            | path       |
            | README.md  |
            | src/main.c |
        And the manifest 'dfetch.yaml' in MyProject
            """
            manifest:
              version: '0.0'
              projects:
                - name: SomeProject
                  url: some-remote-server/SomeProject.tar.gz
                  vcs: archive
            """
        When I run "dfetch update" in MyProject
        Then 'MyProject' looks like:
            """
            MyProject/
                SomeProject/
                    .dfetch_data.yaml
                    README.md
                    src/
                        main.c
                dfetch.yaml
            """

    Scenario: Zip archive project is fetched
        Given an archive "SomeProject.zip" with the files
            | path          |
            | README.md     |
            | include/lib.h |
        And the manifest 'dfetch.yaml' in MyProject
            """
            manifest:
              version: '0.0'
              projects:
                - name: SomeProject
                  url: some-remote-server/SomeProject.zip
                  vcs: archive
            """
        When I run "dfetch update" in MyProject
        Then 'MyProject' looks like:
            """
            MyProject/
                SomeProject/
                    .dfetch_data.yaml
                    README.md
                    include/
                        lib.h
                dfetch.yaml
            """

    Scenario: Archive projects with sha256, sha384 and sha512 hash verification are fetched
        Given an archive "SomeProject.tar.gz" with the files
            | path      |
            | README.md |
        And the manifest 'dfetch.yaml' in MyProject
            """
            manifest:
              version: '0.0'
              projects:
                - name: SomeProject-sha256
                  url: some-remote-server/SomeProject.tar.gz
                  vcs: archive
                  integrity:
                    hash: sha256:<archive-sha256>
                - name: SomeProject-sha384
                  url: some-remote-server/SomeProject.tar.gz
                  vcs: archive
                  integrity:
                    hash: sha384:<archive-sha384>
                - name: SomeProject-sha512
                  url: some-remote-server/SomeProject.tar.gz
                  vcs: archive
                  integrity:
                    hash: sha512:<archive-sha512>
            """
        When I run "dfetch update" in MyProject
        Then 'MyProject' looks like:
            """
            MyProject/
                SomeProject-sha256/
                    .dfetch_data.yaml
                    README.md
                SomeProject-sha384/
                    .dfetch_data.yaml
                    README.md
                SomeProject-sha512/
                    .dfetch_data.yaml
                    README.md
                dfetch.yaml
            """

    Scenario: Archive with incorrect sha256 hash is rejected
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
                    hash: sha256:0000000000000000000000000000000000000000000000000000000000000000
            """
        When I run "dfetch update" in MyProject
        Then the output shows
            """
            Dfetch (0.13.0)
              SomeProject:
              > Hash mismatch for SomeProject! sha256 expected 0000000000000000000000000000000000000000000000000000000000000000
            """

    Scenario: Specific directory from archive can be fetched
        Given an archive "SomeProject.tar.gz" with the files
            | path              |
            | src/main.c        |
            | src/lib.c         |
            | tests/test_main.c |
        And the manifest 'dfetch.yaml' in MyProject
            """
            manifest:
              version: '0.0'
              projects:
                - name: SomeProject
                  url: some-remote-server/SomeProject.tar.gz
                  vcs: archive
                  src: src/
            """
        When I run "dfetch update" in MyProject
        Then 'MyProject' looks like:
            """
            MyProject/
                SomeProject/
                    .dfetch_data.yaml
                    lib.c
                    main.c
                dfetch.yaml
            """

    Scenario: Files can be ignored when fetching from archive
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
        When I run "dfetch update" in MyProject
        Then 'MyProject' looks like:
            """
            MyProject/
                SomeProject/
                    .dfetch_data.yaml
                    README.md
                    src/
                        main.c
                dfetch.yaml
            """

    Scenario: Archive is re-fetched when force flag is given
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
        When I run "dfetch update --force" in MyProject
        Then the output shows
            """
            Dfetch (0.13.0)
              SomeProject:
              > Fetched some-remote-server/SomeProject.tar.gz
            """

    Scenario: Multiple archive projects are fetched
        Given an archive "LibA.tar.gz" with the files
            | path      |
            | README.md |
        And an archive "LibB.zip" with the files
            | path      |
            | README.md |
        And the manifest 'dfetch.yaml' in MyProject
            """
            manifest:
              version: '0.0'
              projects:
                - name: LibA
                  url: some-remote-server/LibA.tar.gz
                  vcs: archive

                - name: LibB
                  url: some-remote-server/LibB.zip
                  vcs: archive
            """
        When I run "dfetch update" in MyProject
        Then the following projects are fetched
            | path           |
            | MyProject/LibA |
            | MyProject/LibB |

    Scenario: Archive with internal relative symlink using .. is fetched safely
        Given an archive "SomeProject.tar.gz" with the files
            | path             |
            | README.md        |
            | other/target.mk  |
        And the archive "SomeProject.tar.gz" contains a symlink "sub/dir/link.mk" pointing to "../../other/target.mk"
        And the manifest 'dfetch.yaml' in MyProject
            """
            manifest:
              version: '0.0'
              projects:
                - name: SomeProject
                  url: some-remote-server/SomeProject.tar.gz
                  vcs: archive
            """
        When I run "dfetch update" in MyProject
        Then 'MyProject' looks like:
            """
            MyProject/
                SomeProject/
                    .dfetch_data.yaml
                    README.md
                    other/
                        target.mk
                    sub/
                        dir/
                            link.mk
                dfetch.yaml
            """
        And 'MyProject/SomeProject/sub/dir/link.mk' is a symlink pointing to '../../other/target.mk'
