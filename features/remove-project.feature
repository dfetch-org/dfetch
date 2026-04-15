@remove
Feature: Remove a project from the manifest

    During the lifetime of a project, dependencies come and go. When a vendored
    library is no longer needed, *DFetch* can remove it from the manifest **and**
    delete the fetched files in one step with ``dfetch remove <name>``.

    Background:
        Given a git repository "LibAlpha.git"
        And a git repository "LibBeta.git"
        And the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              projects:
                - name: lib-alpha
                  url: some-remote-server/LibAlpha.git
                  dst: ext/lib-alpha

                - name: lib-beta
                  url: some-remote-server/LibBeta.git
                  dst: ext/lib-beta

            """
        And all projects are updated

  Scenario: Remove an existing project
     Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              projects:
                - name: lib-alpha
                  url: some-remote-server/LibAlpha.git
                  dst: ext/lib-alpha

                - name: lib-beta
                  url: some-remote-server/LibBeta.git
                  dst: ext/lib-beta

            """
    When I run "dfetch remove lib-alpha"
    Then the manifest 'dfetch.yaml' is replaced with
            """
            manifest:
              version: '0.0'

              projects:
              - name: lib-beta
                url: some-remote-server/LibBeta.git
                dst: ext/lib-beta

            """
    And the directory 'ext/lib-alpha' should be removed from disk
    And the output shows
            """
            Dfetch (0.13.0)
              lib-alpha:
              > removed
            """

  Scenario: Remove multiple projects atomically
     Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              projects:
                - name: lib-alpha
                  url: some-remote-server/LibAlpha.git
                  dst: ext/lib-alpha

                - name: lib-beta
                  url: some-remote-server/LibBeta.git
                  dst: ext/lib-beta

            """
    When I run "dfetch remove lib-alpha lib-beta"
    Then the manifest 'dfetch.yaml' is replaced with
            """
            manifest:
              version: '0.0'

              projects: []

            """
    And the directory 'ext/lib-alpha' should be removed from disk
    And the directory 'ext/lib-beta' should be removed from disk
    And the output shows
            """
            Dfetch (0.13.0)
              lib-alpha:
              > removed
              lib-beta:
              > removed
            """

  Scenario: Removing a project that does not exist in the manifest is reported
     Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              projects:
                - name: lib-alpha
                  url: some-remote-server/LibAlpha.git
                  dst: ext/lib-alpha

                - name: lib-beta
                  url: some-remote-server/LibBeta.git
                  dst: ext/lib-beta

            """
    When I run "dfetch remove lib-alpha lib-unknown lib-beta"
    Then the manifest 'dfetch.yaml' is replaced with
            """
            manifest:
              version: '0.0'

              projects: []

            """
    And the directory 'ext/lib-alpha' should be removed from disk
    And the directory 'ext/lib-beta' should be removed from disk
    And the output shows
            """
            Dfetch (0.13.0)
              lib-unknown:
              > project 'lib-unknown' not found in manifest
              lib-alpha:
              > removed
              lib-beta:
              > removed
            """

  Scenario: Removing a project that was never fetched still removes it from the manifest
     Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              projects:
                - name: lib-gamma
                  url: some-remote-server/LibBeta.git
                  dst: ext/lib-gamma

                - name: lib-alpha
                  url: some-remote-server/LibAlpha.git
                  dst: ext/lib-alpha

            """
    And the directory 'ext/lib-gamma' does not exist on disk
    When I run "dfetch remove lib-gamma"
    Then the manifest 'dfetch.yaml' is replaced with
            """
            manifest:
              version: '0.0'

              projects:
              - name: lib-alpha
                url: some-remote-server/LibAlpha.git
                dst: ext/lib-alpha

            """
    And the output shows
            """
            Dfetch (0.13.0)
              lib-gamma:
              > removed
            """
