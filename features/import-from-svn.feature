Feature: Importing externals from an existing svn repository

    One alternative to *Dfetch* is svn externals. To make the transition
    as easy as possible, a user should be able to generate a manifest that
    is filled with the externals and their pinned versions.

    @remote-svn
    Scenario: Multiple externals are imported
        Given a svn repo with the following externals
            | path       | url                                                       | revision       |
            | ext/cunit1 | https://svn.code.sf.net/p/cunit/code/trunk/Man            | 170            |
            | ext/cunit2 | https://svn.code.sf.net/p/cunit/code/branches/mingw64/Man | 150            |
            | ext/cunit3 | https://svn.code.sf.net/p/cunit/code                      |                |
        When I run "dfetch import"
        Then it should generate the manifest 'dfetch.yaml'
            """
            manifest:
                version: '0.0'

                remotes:
                - name: svn-code-sf-net-p-cunit
                  url-base: https://svn.code.sf.net/p/cunit

                projects:
                - name: ext/cunit1
                  revision: '170'
                  src: Man
                  dst: ./ext/cunit1
                  repo-path: code

                - name: ext/cunit2
                  revision: '150'
                  src: Man
                  dst: ./ext/cunit2
                  branch: mingw64
                  repo-path: code

                - name: ext/cunit3
                  dst: ./ext/cunit3
                  branch: ' '
                  repo-path: code

            """
