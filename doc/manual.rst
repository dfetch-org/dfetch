

Manual
======

*Dfetch* acts on the projects listed in the :ref:`Manifest`.
Each action is a separate sub-command. Commands are grouped here from the
core day-to-day workflow through patch management and CI/CD integration.
For a step-by-step walkthrough see :doc:`getting_started`.

.. program-output:: dfetch --help
   :shell:

.. uml:: /static/uml/commands.puml

----

Foundational
------------

These five commands cover the complete everyday workflow: create or migrate a
manifest, register new dependencies, check for newer versions upstream, and
fetch them into your repository.

Init
~~~~
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: init

.. asciinema:: asciicasts/init.cast

.. automodule:: dfetch.commands.init

Import
~~~~~~
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: import

.. asciinema:: asciicasts/import.cast

.. automodule:: dfetch.commands.import_

Add
~~~
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: add

.. automodule:: dfetch.commands.add

Check
~~~~~
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: check

.. asciinema:: asciicasts/check.cast

.. automodule:: dfetch.commands.check

Update
~~~~~~
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: update

.. asciinema:: asciicasts/update.cast

.. automodule:: dfetch.commands.update

----

Patching
--------

*Dfetch* has a first-class patch workflow. ``dfetch diff`` captures local
changes as numbered patch files that are re-applied automatically on every
``dfetch update``. When a fix is ready to share upstream, ``dfetch
format-patch`` produces a contributor-ready unified diff.

Diff
~~~~
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: diff

.. asciinema:: asciicasts/diff.cast

.. automodule:: dfetch.commands.diff

Update patch
~~~~~~~~~~~~
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: update-patch

.. asciinema:: asciicasts/update-patch.cast

.. automodule:: dfetch.commands.update_patch

Format patch
~~~~~~~~~~~~
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: format-patch

.. asciinema:: asciicasts/format-patch.cast

.. automodule:: dfetch.commands.format_patch

----

CI/CD Integration
-----------------

These commands are designed to plug into automated pipelines. Use ``dfetch
check`` report formats to surface stale or vulnerable dependencies in your
existing security toolchain. Use ``dfetch report`` to generate SBOMs and
inventory lists for compliance audits.

Reporting
~~~~~~~~~
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

Report
~~~~~~
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: report

.. asciinema:: asciicasts/report.cast

.. automodule:: dfetch.commands.report

List (default)
''''''''''''''
.. automodule:: dfetch.reporting.stdout_reporter

Software Bill-of-Materials
''''''''''''''''''''''''''
.. automodule:: dfetch.reporting.sbom_reporter

.. asciinema:: asciicasts/sbom.cast

----

Utilities
---------

Supporting commands for day-to-day maintenance: pin all versions to their
current state, verify your environment is correctly set up, and validate a
manifest without running a fetch.

Freeze
~~~~~~
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: freeze

.. asciinema:: asciicasts/freeze.cast

.. automodule:: dfetch.commands.freeze

Environment
~~~~~~~~~~~
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: environment

.. asciinema:: asciicasts/environment.cast

.. automodule:: dfetch.commands.environment

Validate
~~~~~~~~
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: validate

.. asciinema:: asciicasts/validate.cast

.. automodule:: dfetch.commands.validate
