

Commands
========

*Dfetch* is driven entirely from the command line. Each subcommand
operates on the projects listed in the :ref:`Manifest`, which
*Dfetch* searches for automatically from the current directory recursively
downward.

This page is the complete CLI reference — flags, arguments, and
behaviour for every subcommand. If you are new to *Dfetch*, start with
:doc:`../tutorials/getting_started` instead. For specific tasks the How-to Guides
in the sidebar go further.

.. program-output:: dfetch --help
   :shell:

Init
----
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: init

.. asciinema:: ../asciicasts/init.cast

.. automodule:: dfetch.commands.init

Import
------
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: import

.. asciinema:: ../asciicasts/import.cast

.. automodule:: dfetch.commands.import_

.. seealso:: :doc:`../howto/migration` — step-by-step guide for switching from Git submodules or SVN externals.

Add
---
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: add

.. automodule:: dfetch.commands.add

.. seealso:: :doc:`../howto/adding-a-project` — walks through adding a new dependency from start to finish.

Remove
------
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: remove

.. asciinema:: ../asciicasts/remove.cast

.. automodule:: dfetch.commands.remove

.. seealso:: :doc:`../howto/remove-a-project` — how to remove projects from your manifest.

Check
-----
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: check

.. asciinema:: ../asciicasts/check.cast

.. automodule:: dfetch.commands.check

.. seealso:: :doc:`../howto/check-ci` — how to run dependency checks in CI pipelines and interpret the output formats.

Update
------
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: update

.. asciinema:: ../asciicasts/update.cast

.. automodule:: dfetch.commands.update

.. seealso:: :doc:`../howto/updating-projects` — covers the update workflow, pinning versions, and force-fetching.

Diff
----
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: diff

.. asciinema:: ../asciicasts/diff.cast

.. seealso:: :doc:`../howto/patching` — creating, applying, and maintaining patches across upstream version bumps.

Update patch
------------
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: update-patch

.. asciinema:: ../asciicasts/update-patch.cast

.. _format-patch:

Format patch
------------
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: format-patch

.. asciinema:: ../asciicasts/format-patch.cast

Report
------
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: report

.. asciinema:: ../asciicasts/report.cast

.. automodule:: dfetch.reporting.stdout_reporter

.. seealso:: :doc:`../howto/sbom` — generating a Software Bill of Materials with ``dfetch report``.

Freeze
------
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: freeze

.. asciinema:: ../asciicasts/freeze.cast

.. automodule:: dfetch.commands.freeze

Environment
-----------
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: environment

.. asciinema:: ../asciicasts/environment.cast

.. automodule:: dfetch.commands.environment

Validate
--------
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: validate

.. asciinema:: ../asciicasts/validate.cast

.. automodule:: dfetch.commands.validate
