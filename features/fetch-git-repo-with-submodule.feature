Feature: Fetch projects with nested VCS dependencies

    Some projects include nested version control dependencies
    such as Git submodules or other externals
    These dependencies must be fetched at the exact revision
    pinned by the parent repository to ensure reproducibility

    Background:
        Given a git-repository "SomeInterestingProject.git" with the following submodules
            | path           | url                                     | revision                                 |
            | ext/test-repo1 | https://github.com/dfetch-org/test-repo | e1fda19a57b873eb8e6ae37780594cbb77b70f1a |
            | ext/test-repo2 | https://github.com/dfetch-org/test-repo | 8df389d0524863b85f484f15a91c5f2c40aefda1 |

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
              > Found & fetched submodule "./ext/test-repo1"  (https://github.com/dfetch-org/test-repo @ main - e1fda19a57b873eb8e6ae37780594cbb77b70f1a)
              > Found & fetched submodule "./ext/test-repo2"  (https://github.com/dfetch-org/test-repo @ v1)
              > Fetched master - 79698c99152e4a4b7b759c9def50a130bc91a2ff
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
                            .git/
                            .gitignore
                            LICENSE
                            README.md
                        test-repo2/
                            .git/
                            .gitignore
                            LICENSE
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
                  url             : https://github.com/dfetch-org/test-repo
                  branch          : main
                  tag             : <none>
                  revision        : e1fda19a57b873eb8e6ae37780594cbb77b70f1a
                  source-type     : git-submodule

                - path            : ext/test-repo2
                  url             : https://github.com/dfetch-org/test-repo
                  branch          : <none>
                  tag             : v1
                  revision        : 8df389d0524863b85f484f15a91c5f2c40aefda1
                  source-type     : git-submodule
            """
