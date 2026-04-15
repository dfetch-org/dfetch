@add
Feature: Add a project to the manifest via the CLI

    *DFetch* can add a new project entry to the manifest without requiring
    manual YAML editing. ``dfetch add <url>`` inspects the remote repository,
    fills in sensible defaults (name, destination, default branch), shows a
    preview, and appends the entry to ``dfetch.yaml``.

    Use ``--name``, ``--dst``, ``--version``, ``--src``, ``--ignore`` to
    pre-fill individual fields.

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
        When I run "dfetch add some-remote-server/MyLib.git"
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
        When I run "dfetch add some-remote-server/MyLib.git"
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
        When I run "dfetch add some-remote-server/MyLib.git"
        Then the manifest 'dfetch.yaml' contains entry
            """
              - name: MyLib
                url: some-remote-server/MyLib.git
                branch: master
                dst: ext/MyLib
            """

    Scenario: Non-interactive add with field overrides
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'
              projects:
                - name: ext/existing
                  url: some-remote-server/existing.git
            """
        When I run "dfetch add some-remote-server/MyLib.git --name my-lib --dst libs/my-lib"
        Then the manifest 'dfetch.yaml' contains entry
            """
              - name: my-lib
                url: some-remote-server/MyLib.git
                branch: master
                dst: libs/my-lib
            """
