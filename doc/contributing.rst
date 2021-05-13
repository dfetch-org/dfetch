.. Dfetch documentation master file

Contributing
============
Before implementing a feature please ask one of the maintainers to avoid any unnecessary or double work.
Let other people know through the relevant GitHub issue that you are planning on implementing it.
Also for new features, first create an issue that can be discussed.

After implementing (with tests and documentation) create a PR on Github and let your changes be reviewed.

Virtual Environment
-------------------
Create a virtual environment by double-clicking ``create_venv.py`` or by running the following command.
This will install all develop dependencies from ``requirements.txt``, install `DFetch` as
`editable package <https://pip.pypa.io/en/stable/cli/pip_wheel/?highlight=editable#cmdoption-e>`_ and
install all runtime dependencies from ``setup.py``.

.. code-block:: bash

    python create_venv.py

.. important :: *dfetch* is primarily developed with python 3.7

Running in VSCode
-----------------
To debug or run directly from VSCode create the :ref:`virtual environment`.
Select the python from the virtual environment.
Add the following configuration to the ``.vscode/launch.json``.

.. code-block:: javascript

    "configurations": [
        {
            "name": "Python: Module",
            "type": "python",
            "request": "launch",
            "module": "dfetch.main",
            "justMyCode": false,
            "args": ["update"]
        }
    ]

For on-the-fly linting add the following to your ``.vscode/settings.json``:

.. code-block:: javascript

    {
        "python.pythonPath": "${workspaceFolder}/venv/Scripts/python",
        "python.linting.prospectorEnabled": true,
        "python.linting.lintOnSave": true,

        "restructuredtext.linter.name": "doc8",
        "restructuredtext.builtDocumentationPath" : "${workspaceRoot}/doc/_build/html",
        "restructuredtext.confPath"               : "${workspaceRoot}/doc",
        "restructuredtext.linter.run": "onType",
        "restructuredtext.linter.extraArgs": [
            "--config", "${workspaceFolder}/setup.cfg"
        ]
    }

For configuring the testing, add below section to your workspace settings in ``.vscode/settings.json``:

.. code-block:: javascript

    {
        "python.testing.pytestArgs": [
            "tests"
        ],
        "python.testing.unittestEnabled": false,
        "python.testing.nosetestsEnabled": false,
        "python.testing.pytestEnabled": true
    }

Quality
-------
To avoid any discussion about formatting `black <https://github.com/psf/black>`_ is used as code formatter.
Next to that `isort <https://github.com/PyCQA/isort>`_ is used for sorting the imports.
And `doc8 <https://github.com/pycqa/doc8>`_ is used as rst linter.

Run `check_quality.bat` (or GitHub will run it for you).

Testing
-------

Unit tests
~~~~~~~~~~
`pytest <https://docs.pytest.org/en/latest/>`_ is used as testing framework. All code contributed should be accompanied with unit tests.
Tests can be found in the ``tests`` folder.

To see coverage, in the virtual environment run ``pytest`` with coverage

.. code-block:: bash

    pytest --cov=dfetch tests

Feature tests
~~~~~~~~~~~~~
Feature tests are used for higher-level integration testing of functionality.
For this `behave <https://behave.readthedocs.io/en/latest/>`_ is used as testing framework.
Features are specified in *Gherkin* in so-called feature files in the ``features`` folder.
The sentences in the feature files, map to steps in the ``features/steps`` folder.

Test can be run directly from the command-line

.. code-block:: bash

    behave features

To debug these tests, mark the ``Feature:`` or ``Scenario:`` to debug with the ``@wip`` tag
and add the following configuration to your ``launch.json``.

.. code-block:: javascript

    "configurations": [

        {
            "name": "Feature tests (wip)",
            "type": "python",
            "justMyCode": false,
            "console": "integratedTerminal",
            "request": "launch",
            "module": "behave",
            "args": [
                "features", "--wip"
            ]
        },
    ]

Creating documentation
----------------------
Run ``create_docs.bat`` and open ``index.html`` in ``doc/_build/html`` to read it.
See `This example <https://pythonhosted.org/an_example_pypi_project/sphinx.html>`_ for documenting the code.


Releasing
---------

- Update ``CHANGELOG.rst`` with release date.
- Bump version number in ``dfetch/__init__.py``.
- Create annotated tag and push it:

.. code-block:: bash

    git tag -a 'v0.0.2' -m "Release version v0.0.2"
    git push --tags

- If all tests ok, create release in the `GitHub webui <https://github.com/dfetch-org/dfetch/releases/new>`_.
- When the release is created, a new package is automatically pushed to `PyPi <https://pypi.org/project/dfetch/>`_.

- After release, add new header to ``CHANGELOG.rst``:

.. code-block:: rst

    Release 0.0.3 (In development)
    ===================================
