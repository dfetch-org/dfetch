@remote-svn
Feature: Patch after fetching from svn repo

    Sometimes a patch needs to be applied after fetching. *DFetch* makes it
    possible to specify a patch file.

    Scenario: A patch file is applied after fetching
        Given the manifest 'dfetch.yaml'
            """
            manifest:
                version: '0.0'

                remotes:
                - name: cutter
                  url-base: svn://svn.code.sf.net/p/cutter/svn/cutter

                projects:
                - name: cutter
                  vcs: svn
                  tag: 1.1.7
                  dst: ext/cutter
                  patch: diff.patch
                  src: apt
            """
        And the patch file 'diff.patch'
            """
            Index: build-deb.sh
            ===================================================================
            --- build-deb.sh	(revision 4007)
            +++ build-deb.sh	(working copy)
            @@ -1,1 +1,1 @@
            -#!/bin/sh
            +#!/bin/bash
            """
        When I run "dfetch update"
        Then the first line of 'ext/cutter/build-deb.sh' is changed to
            """
            #!/bin/bash
            """

    Scenario: Applying patch file fails
        Given the manifest 'dfetch.yaml'
            """
            manifest:
                version: '0.0'

                remotes:
                - name: cutter
                  url-base: svn://svn.code.sf.net/p/cutter/svn/cutter

                projects:
                - name: cutter
                  vcs: svn
                  tag: 1.1.7
                  dst: ext/cutter
                  patch: diff.patch
                  src: apt
            """
        And the patch file 'diff.patch'
            """
            Index: build-deb.sh
            ===================================================================
            --- build-deb2.sh	(revision 4007)
            +++ build-deb2.sh	(working copy)
            @@ -1,1 +1,1 @@
            -#!/bin/sh
            +#!/bin/bash
            """
        When I run "dfetch update"
        Then the output shows
            """
            Dfetch (0.9.1)
              cutter              : Fetched 1.1.7
            source/target file does not exist:
              --- b'build-deb2.sh'
              +++ b'build-deb2.sh'
            Applying patch "diff.patch" failed
            """
