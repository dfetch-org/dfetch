Feature: Check for dependencies in projects

    When a project has dependencies of its own, it can list them using its own
    manifest. *Dfetch* should recommend the user to add these dependencies to
    the manifest.

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
            Dfetch (0.8.0)
              SomeProject         : wanted (v1), available (v1)
            """

    Scenario: A recommendation is done due to a missing dependency
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
                      url: some-remote-server/SomeOtherProject.git
                      tag: v1
            """
        And a git repository "SomeOtherProject.git"
        And all projects are updated in MyProject
        When I run "dfetch check" in MyProject
        Then the output shows
            """
            Dfetch (0.8.0)
            Multiple manifests found, using dfetch.yaml
              SomeProject         : up-to-date (v1)

            "SomeProject" depends on the following project(s) which are not part of your manifest:
            (found in ThirdParty/SomeProject/dfetch.yaml)

            -   name: SomeOtherProject
                url: some-remote-server/SomeOtherProject.git
                tag: v1
            """

    Scenario: No recommendation is done
        Given the manifest 'dfetch.yaml' in MyProject
            """
            manifest:
                version: 0.0
                projects:
                    - name: SomeProject
                      dst: ThirdParty/SomeProject
                      url: some-remote-server/SomeProject.git
                      tag: v1

                    - name: SomeOtherProject
                      url: some-remote-server/SomeOtherProject.git
                      tag: v1
            """
        And a git-repository "SomeProject.git" with the manifest:
            """
            manifest:
                version: 0.0
                projects:
                    - name: SomeOtherProject
                      url: some-remote-server/SomeOtherProject.git
            """
        And a git repository "SomeOtherProject.git"
        And all projects are updated in MyProject
        When I run "dfetch check" in MyProject
        Then the output shows
            """
            Dfetch (0.8.0)
            Multiple manifests found, using dfetch.yaml
              SomeProject         : up-to-date (v1)
              SomeOtherProject    : up-to-date (v1)
            """
