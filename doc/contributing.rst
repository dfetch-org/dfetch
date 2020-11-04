.. Dfetch documentation master file

Contributing
============
Before implementing a feature please ask one of the maintainers to avoid any unnecessary or double work.

Virtual Environment
-------------------
Create a virtual environment by double-clicking ``create_venv.py`` or by running the following command.

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

Quality
-------
To avoid any discussion about formatting `black <https://github.com/psf/black>`_ is used as code formatter.
Next to that `isort <https://github.com/PyCQA/isort>`_ is used for sorting the imports.
And `doc8 <https://github.com/pycqa/doc8>`_ is used as rst linter.

Run `check_quality.bat` (or GitHub will run it for you).

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
