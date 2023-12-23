Feature: Fetch single file from git repo

    Sometimes only one file is enough. *DFetch* makes it possible to specify
    only one file from a repository.

    Scenario: A single file is fetched from a repo
        Given the manifest 'dfetch.yaml' in MyProject
            """
            manifest:
                version: 0.0
                projects:
                    - name: SomeProjectWithAnInterestingFile
                      url: some-remote-server/SomeProjectWithAnInterestingFile.git
                      src: SomeFolder/SomeSubFolder
                      tag: v1
            """
        And a git-repository "SomeProjectWithAnInterestingFile.git" with the files
            | path                                  |
            | SomeFolder/SomeSubFolder/SomeFile.txt |
            | SomeOtherFolder/SomeOtherFile.txt     |
        When I run "dfetch update"
        Then the output shows
            """
            Dfetch (0.8.0)
              SomeProjectWithAnInterestingFile: Fetched v1
            """
        Then 'MyProject' looks like:
            """
            MyProject/
                SomeProjectWithAnInterestingFile/
                    .dfetch_data.yaml
                    SomeFile.txt
                dfetch.yaml
            """

    Scenario: A single file is fetched from a repo (dst)
        Given the manifest 'dfetch.yaml' in MyProject
            """
            manifest:
                version: 0.0
                projects:
                    - name: SomeProjectWithAnInterestingFile
                      url: some-remote-server/SomeProjectWithAnInterestingFile.git
                      dst: ext
                      src: SomeFolder/SomeFile.txt
                      tag: v1
            """
        And a git-repository "SomeProjectWithAnInterestingFile.git" with the files
            | path                                  |
            | SomeFolder/SomeFile.txt               |
            | SomeOtherFolder/SomeOtherFile.txt     |
        When I run "dfetch update"
        Then the output shows
            """
            Dfetch (0.8.0)
              SomeProjectWithAnInterestingFile: Fetched v1
            """
        Then 'MyProject' looks like:
            """
            MyProject/
                dfetch.yaml
                ext/
                    .dfetch_data.yaml
                    SomeFile.txt
            """
