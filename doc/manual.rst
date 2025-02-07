.. Dfetch documentation master file

Manual
======

Init
-----
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: init

.. asciinema:: asciicasts/init.cast

.. automodule:: dfetch.commands.init

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

Update
------
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: update

.. asciinema:: asciicasts/update.cast

.. automodule:: dfetch.commands.update

Validate
--------
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: validate

.. asciinema:: asciicasts/validate.cast

.. automodule:: dfetch.commands.validate

Diff
-----
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: diff

.. asciinema:: asciicasts/diff.cast

.. automodule:: dfetch.commands.diff

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


Import
------
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: import

.. asciinema:: asciicasts/import.cast

.. automodule:: dfetch.commands.import_
