Feature: Fetch with ignore in git

    Sometimes you want to ignore files from a project
    These can be specified using the `ignore:` tag

    Background:
        Given a git-repository "SomeInterestingProject.git" with the files
            | path                                        |
            | SomeFolder/SomeSubFolder/SomeFile.txt       |
            | SomeFolder/SomeSubFolder/OtherFile.txt      |
            | SomeFolder/SomeSubFolder/SomeFile.md        |
            | SomeFolder/SomeOtherSubFolder/SomeFile.txt  |
            | SomeFolder/SomeOtherSubFolder/OtherFile.txt |

    Scenario: A file pattern is fetched from a repo
        Given the manifest 'dfetch.yaml' in MyProject
            """
            manifest:
                version: 0.0
                projects:
                    - name: SomeInterestingProject
                      url: some-remote-server/SomeInterestingProject.git
                      src: SomeFolder/SomeSubFolder
                      ignore:
                         - OtherFile.txt
                      tag: v1
            """
        When I run "dfetch update"
        Then the output shows
            """
            Dfetch (0.9.1)
              SomeInterestingProject: Fetched v1
            """
        Then 'MyProject' looks like:
            """
            MyProject/
                SomeInterestingProject/
                    .dfetch_data.yaml
                    SomeFile.md
                    SomeFile.txt
                dfetch.yaml
            """

    Scenario: Combination of directories and a single file can be ignored
        Given the manifest 'dfetch.yaml' in MyProject
            """
            manifest:
                version: 0.0
                projects:
                    - name: SomeInterestingProject
                      url: some-remote-server/SomeInterestingProject.git
                      ignore:
                         - SomeFolder/SomeOtherSubFolder
                         - SomeFolder/SomeSubFolder/SomeFile.md
                      tag: v1
            """
        When I run "dfetch update"
        Then the output shows
            """
            Dfetch (0.9.1)
              SomeInterestingProject: Fetched v1
            """
        Then 'MyProject' looks like:
            """
            MyProject/
                SomeInterestingProject/
                    .dfetch_data.yaml
                    SomeFolder/
                        SomeSubFolder/
                            OtherFile.txt
                            SomeFile.txt
                dfetch.yaml
            """

    Scenario: Ignore overrides the file pattern match in src attribute
        Given the manifest 'dfetch.yaml' in MyProject
            """
            manifest:
                version: 0.0
                projects:
                    - name: SomeInterestingProject
                      url: some-remote-server/SomeInterestingProject.git
                      src: SomeFolder/SomeSubFolder/*.txt
                      ignore:
                         - /SomeNonExistingPath
                         - SomeFile.*
                      tag: v1
            """
        When I run "dfetch update"
        Then the output shows
            """
            Dfetch (0.9.1)
              SomeInterestingProject: Fetched v1
            """
        Then 'MyProject' looks like:
            """
            MyProject/
                SomeInterestingProject/
                    .dfetch_data.yaml
                    OtherFile.txt
                dfetch.yaml
            """
