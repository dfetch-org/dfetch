Feature: Checking dependencies from a git repository

    *DFetch* can check if there are new versions.

    Scenario: Git projects have changes
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              remotes:
                - name: github-com-dfetch-org
                  url-base: https://github.com/dfetch-org/test-repo

              projects:
                - name: ext/test-repo-rev-only
                  revision: e1fda19a57b873eb8e6ae37780594cbb77b70f1a
                  dst: ext/test-repo-rev-only

                - name: ext/test-rev-and-branch
                  revision: 8df389d0524863b85f484f15a91c5f2c40aefda1
                  branch: main
                  dst: ext/test-rev-and-branch

            """
        When I run "dfetch check"
        Then the output shows
            """
            Dfetch (0.10.0)
              ext/test-repo-rev-only: wanted (e1fda19a57b873eb8e6ae37780594cbb77b70f1a), available (e1fda19a57b873eb8e6ae37780594cbb77b70f1a)
              ext/test-rev-and-branch: wanted (main - 8df389d0524863b85f484f15a91c5f2c40aefda1), available (main - e1fda19a57b873eb8e6ae37780594cbb77b70f1a)
            """

    Scenario: A newer tag is available than in manifest
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              remotes:
                - name: github-com-dfetch-org
                  url-base: https://github.com/dfetch-org/test-repo

              projects:
                - name: ext/test-repo-tag-v1
                  tag: v1
                  dst: ext/test-repo-tag-v1

            """
        When I run "dfetch check"
        Then the output shows
            """
            Dfetch (0.10.0)
              ext/test-repo-tag-v1: wanted (v1), available (v2.0)
            """

   Scenario: Check is done after an update
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              remotes:
                - name: github-com-dfetch-org
                  url-base: https://github.com/dfetch-org/test-repo

              projects:
                - name: ext/test-repo-rev-only
                  revision: e1fda19a57b873eb8e6ae37780594cbb77b70f1a
                  dst: ext/test-repo-rev-only

                - name: ext/test-rev-and-branch
                  revision: 8df389d0524863b85f484f15a91c5f2c40aefda1
                  branch: main
                  dst: ext/test-rev-and-branch

            """
        And all projects are updated
        When I run "dfetch check"
        Then the output shows
            """
            Dfetch (0.10.0)
              ext/test-repo-rev-only: up-to-date (e1fda19a57b873eb8e6ae37780594cbb77b70f1a)
              ext/test-rev-and-branch: wanted & current (main - 8df389d0524863b85f484f15a91c5f2c40aefda1), available (main - e1fda19a57b873eb8e6ae37780594cbb77b70f1a)
            """

    Scenario: Tag is updated in manifest
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              projects:
                - name: ext/test-repo-tag
                  url: https://github.com/dfetch-org/test-repo
                  tag: v1

            """
        And all projects are updated
        When the manifest 'dfetch.yaml' is changed to
            """
            manifest:
              version: '0.0'

              projects:
                - name: ext/test-repo-tag
                  url: https://github.com/dfetch-org/test-repo
                  tag: v2.0

            """
        And I run "dfetch check"
        Then the output shows
            """
            Dfetch (0.10.0)
              ext/test-repo-tag   : wanted (v2.0), current (v1), available (v2.0)
            """

    Scenario: A local change is reported
        Given a git repository "SomeProject.git"
        And a fetched and committed MyProject with the manifest
            """
            manifest:
                version: 0.0
                projects:
                  - name: SomeProject
                    url: some-remote-server/SomeProject.git
            """
        And "SomeProject/README.md" in MyProject is changed and committed with
            """
            An important sentence for the README!
            """
        When I run "dfetch check SomeProject"
        Then the output shows
            """
            Dfetch (0.10.0)
              SomeProject         : Local changes were detected, please generate a patch using 'dfetch diff SomeProject' and add it to your manifest using 'patch:'. Alternatively overwrite the local changes with 'dfetch update --force SomeProject'
              SomeProject         : up-to-date (master - 90be799b58b10971691715bdc751fbe5237848a0)
            """

    Scenario: A non-existent remote is reported
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              projects:
                - name: non-existent-url
                  revision: e1fda19a57b873eb8e6ae37780594cbb77b70f1a
                  dst: ext/test-repo-rev-only
                  url: https://giiiiiidhub.com/i-do-not-exist/broken
            """
        When I run "dfetch check"
        Then the output shows
            """
            Dfetch (0.10.0)
            >>>git ls-remote --heads https://giiiiiidhub.com/i-do-not-exist/broken<<< failed!
            'https://giiiiiidhub.com/i-do-not-exist/broken' is not a valid URL or unreachable:
            fatal: unable to access 'https://giiiiiidhub.com/i-do-not-exist/broken/': Could not resolve host: giiiiiidhub.com
            """

      Scenario: A non-existent tag, branch or revision is reported
        Given a git repository "SomeProject.git"
        And the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              projects:
                - name: SomeProjectMissingTag
                  tag: i-dont-exist
                  url: some-remote-server/SomeProject.git

                - name: SomeProjectNonExistentBranch
                  branch: i-dont-exist
                  url: some-remote-server/SomeProject.git

                - name: SomeProjectNonExistentRevision
                  revision: '0123112321234123512361236123712381239123'
                  url: some-remote-server/SomeProject.git
            """
        When I run "dfetch check"
        Then the output shows
            """
            Dfetch (0.10.0)
              SomeProjectMissingTag: wanted (i-dont-exist), but not available at the upstream.
              SomeProjectNonExistentBranch: wanted (i-dont-exist), but not available at the upstream.
              SomeProjectNonExistentRevision: wanted (0123112321234123512361236123712381239123), but not available at the upstream.
            """
