Feature: Keep license in project

    A lot of people in the world do a lot of hard work to create software
    to use freely. They only ask to keep the license with their code.
    When fetching only a part of a repository with the 'src:' tag, the risk
    is you forget the license file.

    Scenario: License is preserved in git repo sparse checkout
        Given the manifest 'dfetch.yaml' in MyProject
            """
            manifest:
                version: 0.0
                projects:
                    - name: SomeProjectWithLicense
                      url: some-remote-server/SomeProjectWithLicense.git
                      src: SomeFolder/
                      tag: v1
            """
        And a git-repository "SomeProjectWithLicense.git" with the files
            | path                                  |
            | LICENSE                               |
            | SomeFolder/SomeFile.txt               |
            | SomeOtherFolder/SomeOtherFile.txt     |
            | SomeSubFolder/LICENSE                 |
        When I run "dfetch update"
        Then the output shows
            """
            Dfetch (0.8.0)
              SomeProjectWithLicense: Fetched v1
            """
        Then 'MyProject' looks like:
            """
            MyProject/
                SomeProjectWithLicense/
                    .dfetch_data.yaml
                    LICENSE
                    SomeFile.txt
                dfetch.yaml
            """

    Scenario: License is preserved in svn repo sparse checkout
        Given the manifest 'dfetch.yaml' in MyProject
            """
            manifest:
                version: 0.0
                projects:
                    - name: SomeProjectWithLicense
                      url: some-remote-server/SomeProjectWithLicense
                      src: SomeFolder/
            """
        And a svn-server "SomeProjectWithLicense" with the files
            | path                                  |
            | LICENSE                               |
            | SomeFolder/SomeFile.txt               |
            | SomeOtherFolder/SomeOtherFile.txt     |
        When I run "dfetch update"
        Then the output shows
            """
            Dfetch (0.8.0)
              SomeProjectWithLicense: Fetched trunk - 1
            """
        Then 'MyProject' looks like:
            """
            MyProject/
                SomeProjectWithLicense/
                    .dfetch_data.yaml
                    LICENSE
                    SomeFile.txt
                dfetch.yaml
            """

    Scenario: A single file is fetched from svn repo
        Given the manifest 'dfetch.yaml' in MyProject
            """
            manifest:
                version: 0.0
                projects:
                    - name: SomeProjectWithLicense
                      dst: SomeFile.txt
                      url: some-remote-server/SomeProjectWithLicense
                      src: SomeFolder/SomeFile.txt
            """
        And a svn-server "SomeProjectWithLicense" with the files
            | path                                  |
            | COPYING.txt                           |
            | SomeFolder/SomeFile.txt               |
            | SomeOtherFolder/SomeOtherFile.txt     |
        When I run "dfetch update"
        Then the output shows
            """
            Dfetch (0.8.0)
              SomeProjectWithLicense: Fetched trunk - 1
            """
        Then 'MyProject' looks like:
            """
            MyProject/
                .dfetch_data-SomeFile.txt.yaml
                COPYING.txt
                SomeFile.txt
                dfetch.yaml
            """
