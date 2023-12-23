Feature: Fetch file pattern from svn repo

    Sometimes all files matching a pattern can be useful.
    *DFetch* makes it possible to specify a file pattern from a repository.

    Scenario: A file pattern is fetched from a repo
        Given the manifest 'dfetch.yaml' in MyProject
            """
            manifest:
                version: 0.0
                projects:
                    - name: SomeProjectWithAnInterestingFile
                      url: some-remote-server/SomeProjectWithAnInterestingFile
                      src: SomeFolder/SomeSubFolder/*.txt
            """
        And a svn-server "SomeProjectWithAnInterestingFile" with the files
            | path                                   |
            | SomeFolder/SomeSubFolder/SomeFile.txt  |
            | SomeFolder/SomeSubFolder/OtherFile.txt |
            | SomeFolder/SomeSubFolder/SomeFile.md   |
        When I run "dfetch update"
        Then the output shows
            """
            Dfetch (0.8.0)
              SomeProjectWithAnInterestingFile: Fetched trunk - 1
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
