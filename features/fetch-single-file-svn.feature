Feature: Fetch single file from svn repo

    Sometimes only one file is enough. *DFetch* makes it possible to specify
    only one file from a repository.

    Scenario: A single file is fetched from svn repo
        Given the manifest 'dfetch.yaml' in MyProject
            """
            manifest:
                version: 0.0
                projects:
                    - name: SomeProjectWithAnInterestingFile
                      dst: SomeFile.txt
                      url: some-remote-server/SomeProjectWithAnInterestingFile
                      src: SomeFolder/SomeFile.txt
            """
        And a svn-server "SomeProjectWithAnInterestingFile" with the files
            | path                                  |
            | SomeFolder/SomeFile.txt               |
            | SomeOtherFolder/SomeOtherFile.txt     |
        When I run "dfetch update"
        Then the output shows
            """
            Dfetch (0.8.0)
              SomeProjectWithAnInterestingFile: Fetched trunk - 1
            """
        Then 'MyProject' looks like:
            """
            MyProject/
                .dfetch_data-SomeFile.txt.yaml
                SomeFile.txt
                dfetch.yaml
            """
