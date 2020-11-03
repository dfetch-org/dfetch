.. Dfetch documentation master file

Contributing
============
Before implementing a feature please ask one of the maintainers to avoid any unnecessary or double work.

Environment
-----------
Create a virtual environment by double-clicking ``create_venv.py`` or by running the following command.

.. code-block:: bash

    python create_venv.py

Running in VSCode
-----------------
To debug or run directly from VSCode create the :ref:`virtual environment <environment>`.
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
        "python.linting.lintOnSave": true
    }

Quality
-------
To avoid any discussion about formatting `black <https://github.com/psf/black>` is used as code formatter.
Next to that `isort <https://github.com/PyCQA/isort>` is used for sorting the imports.

Run `check_quality.bat` (or GitHub will run it for you).

Creating documentation
----------------------
Run ``create_docs.bat`` and open ``index.html`` in ``doc/_build/html`` to read it.
See `This example <https://pythonhosted.org/an_example_pypi_project/sphinx.html>` for documenting the code.
