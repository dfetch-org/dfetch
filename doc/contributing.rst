.. Dfetch documentation master file

Contributing
============

Environment
-----------
Create a virtual environment using the following command.

.. code-block:: bash

    python create_venv.py

Running in VSCode
-----------------
To debug or run directly from VSCode create the :ref:`virtual environment <environment>`.
Select the python from the virtual environment.
Add the following configuration to the *launch.json*.

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

Quality
-------
Run `check_quality.bat` (or Github will run it for you).

Creating documentation
----------------------
Run `create_docs.bat` and open `index.html` in `doc/_build/html` to read it.
See [This example](https://pythonhosted.org/an_example_pypi_project/sphinx.html) for documenting the code.
