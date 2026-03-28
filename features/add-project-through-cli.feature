Feature: Add a project to the manifest via the CLI

    *DFetch* can add a new project entry to the manifest without requiring
    manual YAML editing. ``dfetch add <url>`` inspects the remote repository,
    fills in sensible defaults (name, destination, default branch), shows a
    preview, and appends the entry to ``dfetch.yaml`` after confirmation.

    Pass ``--force`` / ``-f`` to skip the confirmation prompt.
    Pass ``--interactive`` / ``-i`` to be guided step-by-step through every
    manifest field (name, destination, branch/tag/revision, optional src,
    optional ignore list).

    Background:
        Given a git repository "MyLib.git"

    Scenario: Adding a project appends it to the manifest
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'
              projects:
                - name: ext/existing
                  url: some-remote-server/existing.git
            """
        When I add "some-remote-server/MyLib.git" with force
        Then the manifest 'dfetch.yaml' contains entry
            """
              - name: MyLib
                url: some-remote-server/MyLib.git
                branch: master
                dst: ext/MyLib
            """

    Scenario: Duplicate project name is auto-renamed in non-interactive mode
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'
              projects:
                - name: MyLib
                  url: some-remote-server/MyLib.git
            """
        When I add "some-remote-server/MyLib.git" with force
        Then the manifest 'dfetch.yaml' contains entry
            """
              - name: MyLib-1
                url: some-remote-server/MyLib.git
                branch: master
            """

    Scenario: Destination is guessed from common prefix of existing projects
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'
              projects:
                - name: ext/lib-a
                  url: some-remote-server/lib-a.git
                - name: ext/lib-b
                  url: some-remote-server/lib-b.git
            """
        When I add "some-remote-server/MyLib.git" with force
        Then the manifest 'dfetch.yaml' contains entry
            """
              - name: MyLib
                url: some-remote-server/MyLib.git
                branch: master
                dst: ext/MyLib
            """

    Scenario: Interactive add guides through each field
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'
              projects:
                - name: ext/existing
                  url: some-remote-server/existing.git
            """
        When I interactively add "some-remote-server/MyLib.git" with inputs
            | Question                  | Answer  |
            | Project name              | my-lib  |
            | Destination path          | libs/my |
            | Version                   | master  |
            | Source path               |         |
            | Ignore paths              |         |
            | Add project to manifest?  | y       |
            | Run update                | n       |
        Then the manifest 'dfetch.yaml' contains entry
            """
              - name: my-lib
                url: some-remote-server/MyLib.git
                branch: master
                dst: libs/my
            """

    Scenario: Interactive add with tag version
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'
              projects:
                - name: existing
                  url: some-remote-server/existing.git
            """
        When I interactively add "some-remote-server/MyLib.git" with inputs
            | Question                  | Answer |
            | Project name              | my-lib |
            | Destination path          | my-lib |
            | Version                   | v1     |
            | Source path               |        |
            | Ignore paths              |        |
            | Add project to manifest?  | y      |
            | Run update                | n      |
        Then the manifest 'dfetch.yaml' contains entry
            """
              - name: my-lib
                url: some-remote-server/MyLib.git
                tag: v1
            """

    Scenario: Interactive add with src subpath
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'
              projects:
                - name: existing
                  url: some-remote-server/existing.git
            """
        When I interactively add "some-remote-server/MyLib.git" with inputs
            | Question                  | Answer     |
            | Project name              | my-lib     |
            | Destination path          | my-lib     |
            | Version                   | master     |
            | Source path               | docs/api   |
            | Ignore paths              |            |
            | Add project to manifest?  | y          |
            | Run update                | n          |
        Then the manifest 'dfetch.yaml' contains entry
            """
              - name: my-lib
                url: some-remote-server/MyLib.git
                branch: master
                src: docs/api
            """

    Scenario: Interactive add with ignore list
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'
              projects:
                - name: existing
                  url: some-remote-server/existing.git
            """
        When I interactively add "some-remote-server/MyLib.git" with inputs
            | Question                  | Answer       |
            | Project name              | my-lib       |
            | Destination path          | my-lib       |
            | Version                   | master       |
            | Source path               |              |
            | Ignore paths              | docs, tests  |
            | Add project to manifest?  | y            |
            | Run update                | n            |
        Then the manifest 'dfetch.yaml' contains entry
            """
              - name: my-lib
                url: some-remote-server/MyLib.git
                branch: master
                ignore:
                - docs
                - tests
            """

    Scenario: Interactive add triggers immediate fetch when update is accepted
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'
              projects:
              - name: existing
                url: some-remote-server/existing.git
            """
        When I interactively add "some-remote-server/MyLib.git" with inputs
            | Question                  | Answer |
            | Project name              | MyLib  |
            | Destination path          | MyLib  |
            | Version                   | master |
            | Source path               |        |
            | Ignore paths              |        |
            | Add project to manifest?  | y      |
            | Run update                | y      |
        Then the manifest 'dfetch.yaml' contains entry
            """
              - name: MyLib
                url: some-remote-server/MyLib.git
                branch: master
            """
        And 'MyLib/README.md' exists

    Scenario: Interactive add with abort does not modify manifest
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'
              projects:
                - name: existing
                  url: some-remote-server/existing.git
            """
        When I interactively add "some-remote-server/MyLib.git" with inputs
            | Question                  | Answer |
            | Project name              | MyLib  |
            | Destination path          | MyLib  |
            | Version                   | master |
            | Source path               |        |
            | Ignore paths              |        |
            | Add project to manifest?  | n      |
        Then the manifest 'dfetch.yaml' is replaced with
            """
            manifest:
              version: '0.0'
              projects:
                - name: existing
                  url: some-remote-server/existing.git
            """

    Scenario: Interactive add with empty src (repo root) does not add src field
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'
              projects:
                - name: existing
                  url: some-remote-server/existing.git
            """
        When I interactively add "some-remote-server/MyLib.git" with inputs
            | Question                  | Answer |
            | Project name              | MyLib  |
            | Destination path          | MyLib  |
            | Version                   | master |
            | Source path               |        |
            | Ignore paths              |        |
            | Add project to manifest?  | y      |
            | Run update                | n      |
        Then the manifest 'dfetch.yaml' contains entry
            """
              - name: MyLib
                url: some-remote-server/MyLib.git
                branch: master
            """
        And the manifest 'dfetch.yaml' does not contain 'src:'
