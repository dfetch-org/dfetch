Feature: Use found manifest in project

    When a project has dependencies of its own, *Dfetch* should also fetch any dependencies in
    a manifest of that project.

    Scenario: Git projects are specified in the manifest
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
            manifest:
                version: 0.0
                projects:
                    - name: SomeOtherProject
                      dst: ../SomeOtherProject
                      url: some-remote-server/SomeOtherProject.git
                      tag: v1
            """
        And a git repository "SomeOtherProject.git"
        When I run "dfetch update" in MyProject
        Then the output shows
            """
            Dfetch (0.0.6)
              SomeProject         : Fetched v1
              SomeProject/SomeOtherProject: Fetched v1
            """
        And 'MyProject' looks like:
            """
            MyProject/
                ThirdParty/
                    SomeOtherProject/
                        .dfetch_data.yaml
                        README.md
                    SomeProject/
                        .dfetch_data.yaml
                        README.md
                        dfetch.yaml
                dfetch.yaml
            """

    Scenario: A subproject has an invalid manifest
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
            Dfetch (0.0.6)
              SomeProject         : Fetched v1
            ThirdParty\SomeProject\dfetch.yaml: Schema validation failed:
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
