

Manual
======

*Dfetch* acts on the projects listed in the :ref:`Manifest`.
Each action is a separate sub-command.
For step-by-step guides see :doc:`getting_started`, :doc:`patching`, :doc:`check-ci`, and :doc:`sbom`.

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

See :doc:`patching` for a step-by-step guide to the full patch workflow.

Diff
~~~~
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: diff

.. asciinema:: asciicasts/diff.cast

Update patch
~~~~~~~~~~~~
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: update-patch

.. asciinema:: asciicasts/update-patch.cast

Format patch
~~~~~~~~~~~~
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: format-patch

.. asciinema:: asciicasts/format-patch.cast

----

CI/CD Integration
-----------------

See :doc:`check-ci` for integration guides for Jenkins, GitHub Actions, and GitLab CI.
See :doc:`sbom` for generating a Software Bill-of-Materials.

Report
~~~~~~
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: report

.. asciinema:: asciicasts/report.cast

List (default)
''''''''''''''
.. automodule:: dfetch.reporting.stdout_reporter

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
