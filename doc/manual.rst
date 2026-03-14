

Manual
======

Introduction
------------
*Dfetch* can perform various actions based on the projects listed in the `manifest <manifest>`_.
Each of these actions are a separate command. Below an overview of all available commands and
their usage. For detailed information on each command, please refer to the respective sections below.
For a step-by-step guide see the `Getting Started <getting_started>`_.

.. program-output:: dfetch --help
   :shell:

Init
-----
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: init

.. asciinema:: asciicasts/init.cast

.. automodule:: dfetch.commands.init

Import
------
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: import

.. asciinema:: asciicasts/import.cast

.. automodule:: dfetch.commands.import_

Check
-----
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: check

.. asciinema:: asciicasts/check.cast

.. automodule:: dfetch.commands.check

Reporting
`````````
.. automodule:: dfetch.reporting.check.reporter

Jenkins reporter
''''''''''''''''
.. automodule:: dfetch.reporting.check.jenkins_reporter

.. asciinema:: asciicasts/check-ci.cast

Sarif reporter
''''''''''''''
.. automodule:: dfetch.reporting.check.sarif_reporter

Code-climate reporter
'''''''''''''''''''''
.. automodule:: dfetch.reporting.check.code_climate_reporter

Update
------
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: update

.. asciinema:: asciicasts/update.cast

.. automodule:: dfetch.commands.update

Report
------
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: report

.. asciinema:: asciicasts/report.cast

.. automodule:: dfetch.commands.report

List (default)
``````````````
.. automodule:: dfetch.reporting.stdout_reporter

Software Bill-of-Materials
``````````````````````````
.. automodule:: dfetch.reporting.sbom_reporter

.. asciinema:: asciicasts/sbom.cast

Diff
----
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: diff

.. asciinema:: asciicasts/diff.cast

.. automodule:: dfetch.commands.diff

Update patch
------------
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: update-patch

.. asciinema:: asciicasts/update-patch.cast

.. automodule:: dfetch.commands.update_patch

Format patch
------------
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: format-patch

.. asciinema:: asciicasts/format-patch.cast

.. automodule:: dfetch.commands.format_patch

Freeze
------
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: freeze

.. asciinema:: asciicasts/freeze.cast

.. automodule:: dfetch.commands.freeze

Environment
-----------
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: environment

.. asciinema:: asciicasts/environment.cast

.. automodule:: dfetch.commands.environment

Validate
--------
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: validate

.. asciinema:: asciicasts/validate.cast

.. automodule:: dfetch.commands.validate

Add
---
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: add

.. asciinema:: asciicasts/add.cast

.. automodule:: dfetch.commands.add


CLI Cheatsheet
--------------

A source-only, no-hassle project-dependency aggregator.
It uses a **manifest file** to describe your project's dependencies and fetches them into your codebase.
Also called vendoring. More info: `<https://dfetch.readthedocs.io/en/latest/getting_started.html>`_.

- Start a new manifest (`dfetch.yaml`) with placeholder content:

  .. code-block:: console

     dfetch init

- Generate a manifest from existing git submodules or svn externals:

  .. code-block:: console

     dfetch import

- Check for newer versions of dependencies and create a machine parseable report for your CI:

  .. code-block:: console

     dfetch check [--jenkins-json] [--sarif] [--code-climate] [project]

- Download one or all projects from the manifest:

  .. code-block:: console

     dfetch update [-f] [project]

- Freeze all projects to their current version:

  .. code-block:: console

     dfetch freeze

- Report about the current state of the project(s):

  .. code-block:: console

     dfetch report [-o <filename>] [-t {sbom,list}] [project]
