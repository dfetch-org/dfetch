@update
Feature: Superproject .gitattributes line endings respected on fetch

    When a superproject enforces specific line endings — through
    ``.gitattributes`` (for example ``* text=auto eol=lf``) in a git
    superproject, or ``svn:auto-props`` (for example ``* = svn:eol-style=LF``)
    in an SVN superproject — *DFetch* respects that setting when fetching
    dependencies, so the vendored files always match the project's enforced
    style.

    Scenario Outline: Git superproject forces <eol> on git subproject with <remote_eol> remote content
        Given a git-repository "SomeProject.git" with <remote_eol> content
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
            | remote_eol | eol  |
            | LF         | crlf |
            | CRLF       | lf   |
            | CRLF       | crlf |
            | LF         | lf   |

    Scenario Outline: SVN superproject forces <eol> on git subproject with <remote_eol> remote content
        An SVN superproject declares its line-ending preference with svn's own
        mechanism: the ``svn:auto-props`` property (e.g. ``* = svn:eol-style=LF``).

        Given a git-repository "SomeProject.git" with <remote_eol> content
        And a local svn repo "MyProject" with the manifest
            """
            manifest:
              version: '0.0'

              projects:
                - name: SomeProject
                  url: some-remote-server/SomeProject.git
                  tag: v1
            """
        And svn:auto-props in MyProject requests <eol> line endings
        When I run "dfetch update" in MyProject
        Then 'MyProject/SomeProject/README.md' has <eol> line endings

        Examples:
            | remote_eol | eol  |
            | LF         | crlf |
            | CRLF       | lf   |
            | CRLF       | crlf |
            | LF         | lf   |

    Scenario Outline: SVN superproject forces <eol> on SVN subproject with <remote_eol> remote content
        Given a svn-server "SomeSvnProject" with <remote_eol> content
        And a local svn repo "MyProject" with the manifest
            """
            manifest:
              version: '0.0'

              projects:
                - name: SomeSvnProject
                  url: some-remote-server/SomeSvnProject
                  tag: v1
            """
        And svn:auto-props in MyProject requests <eol> line endings
        When I run "dfetch update" in MyProject
        Then 'MyProject/SomeSvnProject/README.md' has <eol> line endings

        Examples:
            | remote_eol | eol  |
            | LF         | crlf |
            | CRLF       | lf   |
            | CRLF       | crlf |
            | LF         | lf   |

    Scenario: SVN superproject without a preference leaves line endings unchanged
        Without a line-ending preference (``.gitattributes`` in a git
        superproject, ``svn:auto-props`` in an SVN superproject), fetched files
        keep the line endings the remote provides. A stray ``.gitattributes``
        file next to the manifest of an SVN superproject is not used.

        Given a git-repository "SomeProject.git" with CRLF content
        And a local svn repo "MyProject" with the manifest
            """
            manifest:
              version: '0.0'

              projects:
                - name: SomeProject
                  url: some-remote-server/SomeProject.git
                  tag: v1
            """
        And ".gitattributes" in MyProject is changed with
            """
            * text=auto eol=lf
            """
        When I run "dfetch update" in MyProject
        Then 'MyProject/SomeProject/README.md' has CRLF line endings

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

    Scenario: Remote gitattributes eol=crlf for a file type overrides the superproject lf preference
        A remote repo that marks ``*.bat`` files as ``eol=crlf`` in its own
        ``.gitattributes`` keeps those line endings even when the superproject
        globally requests ``lf``, so Windows batch files are never corrupted.

        Given a git-repository "SomeProject.git" with a CRLF "script.bat" and "*.bat eol=crlf" gitattributes
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
        Then 'MyProject/SomeProject/script.bat' has CRLF line endings

    Scenario: Superproject per-file eol attribute is applied when no global preference exists
        A per-file ``eol`` rule in the superproject (e.g. ``*.bat eol=crlf``)
        without a blanket ``* text=auto eol=...`` preference causes DFetch to
        renormalise fetched files to match the per-file eol setting.

        Given a git-repository "SomeProject.git" with a LF "script.bat" file
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
            *.bat eol=crlf
            """
        When I run "dfetch update" in MyProject
        Then 'MyProject/SomeProject/script.bat' has CRLF line endings
