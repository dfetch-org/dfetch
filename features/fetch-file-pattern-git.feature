Feature: Fetch file pattern from git repo

    Sometimes all files matching a pattern can be useful.
    *DFetch* makes it possible to specify a file pattern from a repository.

    Scenario: A file pattern is fetched from a repo
        Given the manifest 'dfetch.yaml' in MyProject
            """
            manifest:
                version: 0.0
                projects:
                    - name: SomeProjectWithAnInterestingFile
                      url: some-remote-server/SomeProjectWithAnInterestingFile.git
                      src: SomeFolder/SomeSubFolder/*.txt
                      tag: v1
            """
        And a git-repository "SomeProjectWithAnInterestingFile.git" with the files
            | path                                   |
            | SomeFolder/SomeSubFolder/SomeFile.txt  |
            | SomeFolder/SomeSubFolder/OtherFile.txt |
            | SomeFolder/SomeSubFolder/SomeFile.md   |
            | SomeFolder/Unrelated.txt               |
            | AlsoUnrelated.txt                      |
        When I run "dfetch update"
        Then the output shows
            """
            Dfetch (0.14.0)
              SomeProjectWithAnInterestingFile:
              > Fetched v1
            """
        Then 'MyProject' looks like:
            """
            MyProject/
                SomeProjectWithAnInterestingFile/
                    .dfetch_data.yaml
                    OtherFile.txt
                    SomeFile.txt
                dfetch.yaml
            """

    Scenario: A file pattern matches two files in different subfolders
        Given the manifest 'dfetch.yaml' in MyProject
            """
            manifest:
                version: 0.0
                projects:
                    - name: SomeProjectWithAnInterestingFile
                      url: some-remote-server/SomeProjectWithAnInterestingFile.git
                      src: SomeFolder/Some*
                      tag: v1
            """
        And a git-repository "SomeProjectWithAnInterestingFile.git" with the files
            | path                                       |
            | SomeFolder/SomeSubFolder/SomeFile.txt      |
            | SomeFolder/SomeOtherSubFolder/SomeFile.txt |
        When I run "dfetch update"
        Then the output shows
            """
            Dfetch (0.14.0)
            The 'src:' filter 'SomeFolder/Some*' matches multiple directories from 'some-remote-server/SomeProjectWithAnInterestingFile.git'. Only considering files in 'SomeFolder/SomeOtherSubFolder'.
              SomeProjectWithAnInterestingFile:
              > Fetched v1
            """
        Then 'MyProject' looks like:
            """
            MyProject/
                SomeProjectWithAnInterestingFile/
                    .dfetch_data.yaml
                    SomeFile.txt
                dfetch.yaml
            """
