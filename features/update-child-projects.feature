Feature: Update child-projects in projects

    When a project has dependencies of its own, *Dfetch* should also fetch any dependencies in
    a manifest of that project.

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
                    - name: SomeProjectWithoutChild2
                      dst: ../SomeProjectWithoutChild2
                      url: some-remote-server/SomeProjectWithoutChild.git
                      tag: v1
            """
        And a git repository "SomeProjectWithoutChild.git"
        When I run "dfetch update" in MyProject
        Then the output shows
            """
            Dfetch (0.0.6)
              SomeProjectWithChild: Fetched v1
              SomeProjectWithChild/SomeProjectWithoutChild2: Fetched v1
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
                    SomeProjectWithoutChild2/
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
            Dfetch (0.0.6)
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

    Scenario: A second update is performed
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
        And all projects are updated in MyProject
        When I run "dfetch update" in MyProject
        Then the output shows
            """
            Dfetch (0.0.6)
            Multiple manifests found, using dfetch.yaml
              SomeProject         : up-to-date (v1)
              SomeProject/SomeOtherProject: up-to-date (v1)
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
