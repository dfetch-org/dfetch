Feature: Check for updates in child projects

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
        When I run "dfetch check" in MyProject
        Then the output shows
            """
            Dfetch (0.5.0)
              SomeProject         : wanted (v1), available (v1)
            """

    Scenario: A check is performed, when child projects fetched
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
        And a new tag "v2" is added to git-repository "SomeProject.git"
        When I run "dfetch check" in MyProject
        Then the output shows
            """
            Dfetch (0.5.0)
            Multiple manifests found, using dfetch.yaml
              SomeProject         : wanted & current (v1), available (v2)
              SomeProject/SomeOtherProject: up-to-date (v1)
            """
