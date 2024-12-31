@remote-svn
Feature: Checking dependencies from a svn repository

    *DFetch* can check if there are new versions in a SVN repository.

    Scenario: SVN projects are specified in the manifest
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              remotes:
                - name: cunit
                  url-base: svn://svn.code.sf.net/p/cunit/code

              projects:
                - name: cunit-svn-rev-only
                  revision: '170'
                  vcs: svn
                  dst: ext/cunit-svn-rev-only

                - name: cunit-svn-rev-and-branch
                  revision: '156'
                  vcs: svn
                  branch: mingw64
                  dst: ext/cunit-svn-rev-and-branch

            """
        When I run "dfetch check"
        Then the output shows
            """
            Dfetch (0.9.1)
              cunit-svn-rev-only  : wanted (170), available (trunk - 170)
              cunit-svn-rev-and-branch: wanted (mingw64 - 156), available (mingw64 - 170)
            """

    Scenario: A newer tag is available than in manifest
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              remotes:
                - name: cutter
                  url-base: svn://svn.code.sf.net/p/cutter/svn/cutter

              projects:
                - name: cutter-svn-tag
                  vcs: svn
                  tag: 1.1.7
                  dst: ext/cutter-svn-tag

            """
        When I run "dfetch check"
        Then the output shows
            """
            Dfetch (0.9.1)
              cutter-svn-tag      : wanted (1.1.7), available (1.1.8)
            """

    Scenario: Check is done after an update
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              remotes:
                - name: cunit
                  url-base: svn://svn.code.sf.net/p/cunit/code
                  default: true

              projects:
                - name: cunit-svn-rev-only
                  revision: '169'
                  vcs: svn
                  dst: ext/cunit-svn-rev-only

                - name: cunit-svn-rev-and-branch
                  revision: '156'
                  vcs: svn
                  branch: mingw64
                  dst: ext/cunit-svn-rev-and-branch

                - name: ext/test-non-standard-svn
                  url: some-remote-server/SomeProject
                  branch: ' '

            """
        And a non-standard svn-server "SomeProject"
        And all projects are updated
        When I run "dfetch check"
        Then the output shows
            """
            Dfetch (0.9.1)
              cunit-svn-rev-only  : wanted (169), current (trunk - 169), available (trunk - 170)
              cunit-svn-rev-and-branch: wanted & current (mingw64 - 156), available (mingw64 - 170)
              ext/test-non-standard-svn: wanted (latest), current (1), available (1)
            """

    Scenario: A non-standard SVN repository can be checked
        Given the manifest 'dfetch.yaml' in MyProject
            """
            manifest:
                version: 0.0
                projects:
                    - name: SomeProject
                      url: some-remote-server/SomeProject
                      branch: ' '
            """
        And a non-standard svn-server "SomeProject"
        And all projects are updated
        When I run "dfetch check" in MyProject
        Then the output shows
            """
            Dfetch (0.9.1)
              SomeProject         : wanted (latest), current (1), available (1)
            """

    Scenario: A non-existent remote is reported
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              projects:
                - name: non-existent-url
                  url: https://giiiiiidhub.com/i-do-not-exist/broken
                  vcs: svn
            """
        When I run "dfetch check"
        Then the output shows
            """
            Dfetch (0.9.1)
            >>>svn info --non-interactive https://giiiiiidhub.com/i-do-not-exist/broken/trunk<<< failed!
            'https://giiiiiidhub.com/i-do-not-exist/broken/trunk' is not a valid URL or unreachable:
            svn: E170013: Unable to connect to a repository at URL 'https://giiiiiidhub.com/i-do-not-exist/broken/trunk'
            svn: E670002: Name or service not known
            """

    Scenario: A non-existent tag in svn repo
        Given the manifest 'dfetch.yaml' in MyProject
            """
            manifest:
              version: '0.0'

              remotes:
                - name: cutter
                  url-base: svn://svn.code.sf.net/p/cutter/svn/cutter

              projects:
                - name: cutter-svn-tag
                  vcs: svn
                  tag: non-existent-tag
            """
        When I run "dfetch check" in MyProject
        Then the output shows
            """
            Dfetch (0.9.1)
              cutter-svn-tag      : wanted (non-existent-tag), but not available at the upstream.
            """
