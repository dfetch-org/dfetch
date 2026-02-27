Feature: Updated project has dependencies

    When a project has dependencies of its own, it can list them using its own
    manifest. *Dfetch* should recommend the user to add these dependencies to
    the manifest.

    Scenario: Git projects are specified in the manifest
        Given the manifest 'dfetch.yaml' in MyProject
            """
            manifest:
                version: 0.0
                projects:
                    - name: SomeProjectWithManifest
                      dst: third-party/SomeProjectWithManifest
                      url: some-remote-server/SomeProjectWithManifest.git
                      tag: v1
                    - name: SomeProjectWithoutManifest
                      dst: third-party/SomeProjectWithoutManifest
                      url: some-remote-server/SomeProjectWithoutManifest.git
                      tag: v1
            """
        And a git-repository "SomeProjectWithManifest.git" with the manifest:
            """
            manifest:
                version: 0.0
                remotes:
                    - name: github-com-dfetch-org
                      url-base: https://github.com/dfetch-org/test-repo

                projects:
                    - name: SomeOtherProject
                      dst: SomeOtherProject
                      url: some-remote-server/SomeOtherProject.git
                      tag: v1

                    - name: ext/test-repo-tag-v1
                      tag: v1
            """
        And a git repository "SomeProjectWithoutManifest.git"
        When I run "dfetch update" in MyProject
        Then the output shows
            """
            Dfetch (0.12.1)
              SomeProjectWithManifest:
              > Fetched v1
              > "SomeProjectWithManifest" depends on the following project(s) which are not part of your manifest:
                (found in third-party/SomeProjectWithManifest/dfetch.yaml)

                -   name: SomeOtherProject
                    url: some-remote-server/SomeOtherProject.git
                    tag: v1
                -   name: ext/test-repo-tag-v1
                    url: https://github.com/dfetch-org/test-repo
                    tag: v1

              SomeProjectWithoutManifest:
              > Fetched v1
            """
        And 'MyProject' looks like:
            """
            MyProject/
                dfetch.yaml
                third-party/
                    SomeProjectWithManifest/
                        .dfetch_data.yaml
                        README.md
                        dfetch.yaml
                    SomeProjectWithoutManifest/
                        .dfetch_data.yaml
                        README.md
            """

    Scenario: A project from a submanifest has an invalid manifest
        Given the manifest 'dfetch.yaml' in MyProject
            """
            manifest:
                version: 0.0
                projects:
                    - name: SomeProject
                      dst: third-party/SomeProject
                      url: some-remote-server/SomeProject.git
                      tag: v1
            """
        And a git-repository "SomeProject.git" with the manifest:
            """
            very-invalid-manifest
            """
        When I run "dfetch update" in MyProject
        Then the output shows
            """
            Dfetch (0.12.1)
              SomeProject:
              > Fetched v1
            SomeProject/dfetch.yaml: Schema validation failed:

                "very-invalid-manifest\n"
                 ^ (line: 1)

            found arbitrary text
            """
        And 'MyProject' looks like:
            """
            MyProject/
                dfetch.yaml
                third-party/
                    SomeProject/
                        .dfetch_data.yaml
                        README.md
                        dfetch.yaml
            """
