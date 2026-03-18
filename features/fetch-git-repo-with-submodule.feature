Feature: Fetch projects with nested VCS dependencies

    Some projects include nested version control dependencies
    such as Git submodules or other externals
    These dependencies must be fetched at the exact revision
    pinned by the parent repository to ensure reproducibility

    Background:
        Given a git repository "TestRepo.git"
        And a git-repository "SomeInterestingProject.git" with the following submodules
            | path           | url                                 | revision |
            | ext/test-repo1 | some-remote-server/TestRepo.git     | master   |
            | ext/test-repo2 | some-remote-server/TestRepo.git     | v1       |

    Scenario: A project with a git submodule is fetched at the pinned revision
        Given the manifest 'dfetch.yaml' in MyProject
            """
            manifest:
                version: 0.0
                projects:
                    - name: my-project-with-submodules
                      url: some-remote-server/SomeInterestingProject.git
            """
        When I run "dfetch update"
        Then the output shows
            """
            Dfetch (0.12.1)
              my-project-with-submodules:
              > Found & fetched submodule "./ext/test-repo1"  (some-remote-server/TestRepo.git @ master - 79698c99152e4a4b7b759c9def50a130bc91a2ff)
              > Found & fetched submodule "./ext/test-repo2"  (some-remote-server/TestRepo.git @ master - 79698c99152e4a4b7b759c9def50a130bc91a2ff)
              > Fetched master - e1fda19a57b873eb8e6ae37780594cbb77b70f1a
            """
        Then 'MyProject' looks like:
            """
            MyProject/
                dfetch.yaml
                my-project-with-submodules/
                    .dfetch_data.yaml
                    README.md
                    ext/
                        test-repo1/
                            README.md
                        test-repo2/
                            README.md
            """

    Scenario: A project with a git submodule that itself has a nested submodule is fetched at the pinned revision
        Given a git repository "LeafProject.git"
        And a git-repository "MiddleProject.git" with the following submodules
            | path     | url                                | revision |
            | ext/leaf | some-remote-server/LeafProject.git | master   |
        And a git-repository "OuterProject.git" with the following submodules
            | path       | url                                  | revision |
            | ext/middle | some-remote-server/MiddleProject.git | master   |
        Given the manifest 'dfetch.yaml' in MyProject
            """
            manifest:
                version: 0.0
                projects:
                    - name: outer-project
                      url: some-remote-server/OuterProject.git
            """
        When I run "dfetch update"
        Then the output shows
            """
            Dfetch (0.12.1)
              outer-project:
              > Found & fetched submodule "./ext/middle"  (some-remote-server/MiddleProject.git @ master - 79698c99152e4a4b7b759c9def50a130bc91a2ff)
              > Fetched master - e1fda19a57b873eb8e6ae37780594cbb77b70f1a
            """
        Then 'MyProject' looks like:
            """
            MyProject/
                dfetch.yaml
                outer-project/
                    .dfetch_data.yaml
                    README.md
                    ext/
                        middle/
                            README.md
                            ext/
                                leaf/
                                    README.md
            """

    Scenario: Submodule changes are reported in the project report
        Given a fetched and committed MyProject with the manifest
            """
            manifest:
                version: 0.0
                projects:
                    - name: my-project-with-submodules
                      url: some-remote-server/SomeInterestingProject.git
            """
        When I run "dfetch report" in MyProject
        Then the output shows
            """
            Dfetch (0.12.1)
              my-project-with-submodules:
              - remote            : <none>
                remote url        : some-remote-server/SomeInterestingProject.git
                branch            : master
                tag               : <none>
                last fetch        : 26/02/2026, 20:28:24
                revision          : 79698c99152e4a4b7b759c9def50a130bc91a2ff
                patch             : <none>
                licenses          : <none>

                dependencies      :
                - path            : ext/test-repo1
                  url             : some-remote-server/TestRepo.git
                  branch          : master
                  tag             : <none>
                  revision        : e1fda19a57b873eb8e6ae37780594cbb77b70f1a
                  source-type     : git-submodule

                - path            : ext/test-repo2
                  url             : some-remote-server/TestRepo.git
                  branch          : master
                  tag             : <none>
                  revision        : 8df389d0524863b85f484f15a91c5f2c40aefda1
                  source-type     : git-submodule
            """

    Scenario: Subfolder is matched through a glob is fetched and submodules are resolved
        Given a git-repository "GlobProject.git" with the following submodules
            | path                     | url                             | revision |
            | some_dir_a/ext/test-repo | some-remote-server/TestRepo.git | master   |
        Given the manifest 'dfetch.yaml' in MyProject
            """
            manifest:
                version: 0.0
                projects:
                    - name: glob-project
                      url: some-remote-server/GlobProject.git
                      src: some_dir_*
            """
        When I run "dfetch update"
        Then the output shows
            """
            Dfetch (0.12.1)
              glob-project:
              > Found & fetched submodule "./some_dir_a/ext/test-repo"  (some-remote-server/TestRepo.git @ master - 79698c99152e4a4b7b759c9def50a130bc91a2ff)
              > Fetched master - e1fda19a57b873eb8e6ae37780594cbb77b70f1a
            """
        Then 'MyProject' looks like:
            """
            MyProject/
                dfetch.yaml
                glob-project/
                    .dfetch_data.yaml
                    ext/
                        test-repo/
                            README.md
            """
