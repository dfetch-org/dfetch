@update
Feature: Superproject .gitattributes line endings respected on fetch

    When a superproject's ``.gitattributes`` file enforces specific line endings
    (for example ``* text=auto eol=lf`` on Windows, or ``* text=auto eol=crlf``
    on Linux), *DFetch* respects that setting when fetching dependencies, so
    the vendored files always match the project's enforced style.

    Scenario: Superproject forces CRLF line endings
        Given a git-repository "SomeProject.git" with LF content
        And a local git repo "MyProject" with the manifest
            """
            manifest:
              version: '0.0'

              projects:
                - name: SomeProject
                  url: some-remote-server/SomeProject.git
                  tag: v1
            """
        And ".gitattributes" in MyProject is created and committed with
            """
            * text=auto eol=crlf
            """
        When I run "dfetch update" in MyProject
        Then 'MyProject/SomeProject/README.md' has CRLF line endings

    Scenario: Superproject forces LF line endings
        Given a git-repository "SomeProject.git" with CRLF content
        And a local git repo "MyProject" with the manifest
            """
            manifest:
              version: '0.0'

              projects:
                - name: SomeProject
                  url: some-remote-server/SomeProject.git
                  tag: v1
            """
        And ".gitattributes" in MyProject is created and committed with
            """
            * text=auto eol=lf
            """
        When I run "dfetch update" in MyProject
        Then 'MyProject/SomeProject/README.md' has LF line endings
