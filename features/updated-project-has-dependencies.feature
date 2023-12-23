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
                    - name: SomeProjectWithChild
                      dst: ThirdParty/SomeProjectWithChild
                      url: some-remote-server/SomeProjectWithChild.git
                      tag: v1
                    - name: SomeProjectWithoutChild
                      dst: ThirdParty/SomeProjectWithoutChild
                      url: some-remote-server/SomeProjectWithoutChild.git
                      tag: v1
            """
        And a git-repository "SomeProjectWithChild.git" with the manifest:
            """
            manifest:
                version: 0.0
                projects:
                    - name: SomeOtherProject
                      dst: SomeOtherProject
                      url: some-remote-server/SomeOtherProject.git
                      tag: v1
            """
        And a git repository "SomeProjectWithoutChild.git"
        When I run "dfetch update" in MyProject
        Then the output shows
            """
            Dfetch (0.8.0)
              SomeProjectWithChild: Fetched v1

            "SomeProjectWithChild" depends on the following project(s) which are not part of your manifest:
            (found in ThirdParty/SomeProjectWithChild/dfetch.yaml)

            -   name: SomeOtherProject
                url: some-remote-server/SomeOtherProject.git
                tag: v1

              SomeProjectWithoutChild: Fetched v1
            """
        And 'MyProject' looks like:
            """
            MyProject/
                ThirdParty/
                    SomeProjectWithChild/
                        .dfetch_data.yaml
                        README.md
                        dfetch.yaml
                    SomeProjectWithoutChild/
                        .dfetch_data.yaml
                        README.md
                dfetch.yaml
            """

    Scenario: A child-project has an invalid manifest
        Given the manifest 'dfetch.yaml' in MyProject
            """
            manifest:
                version: 0.0
                projects:
                    - name: SomeProject
                      dst: ThirdParty/SomeProject
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
            Dfetch (0.8.0)
              SomeProject         : Fetched v1
            SomeProject/dfetch.yaml: Schema validation failed:
             - Value 'very-invalid-manifest' is not a dict. Value path: ''.
            """
        And 'MyProject' looks like:
            """
            MyProject/
                ThirdParty/
                    SomeProject/
                        .dfetch_data.yaml
                        README.md
                        dfetch.yaml
                dfetch.yaml
            """
