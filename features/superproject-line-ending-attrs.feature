@update
Feature: Superproject .gitattributes line endings respected on fetch

    When a superproject's ``.gitattributes`` file enforces specific line endings
    (for example ``* text=auto eol=lf`` on Windows, or ``* text=auto eol=crlf``
    on Linux), *DFetch* respects that setting when fetching dependencies, so
    the vendored files always match the project's enforced style.

    Scenario Outline: Superproject forces <eol> line endings on git subproject
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
            * text=auto eol=<eol>
            """
        When I run "dfetch update" in MyProject
        Then 'MyProject/SomeProject/README.md' has <eol> line endings

        Examples:
            | eol  |
            | crlf |
            | lf   |

    Scenario Outline: Git superproject forces <eol> on SVN subproject with <remote_eol> remote content
        Given a svn-server "SomeSvnProject" with <remote_eol> content
        And a local git repo "MyProject" with the manifest
            """
            manifest:
              version: '0.0'

              projects:
                - name: SomeSvnProject
                  url: some-remote-server/SomeSvnProject
                  tag: v1
            """
        And ".gitattributes" in MyProject is created and committed with
            """
            * text=auto eol=<eol>
            """
        When I run "dfetch update" in MyProject
        Then 'MyProject/SomeSvnProject/README.md' has <eol> line endings

        Examples:
            | remote_eol | eol  |
            | LF         | crlf |
            | CRLF       | lf   |
            | CRLF       | crlf |
            | LF         | lf   |
