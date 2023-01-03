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
This will install all ``develop`` dependencies from ``pyproject.toml``, install *DFetch* as
`editable package <https://pip.pypa.io/en/stable/cli/pip_wheel/?highlight=editable#cmdoption-e>`_ and
install all runtime dependencies from ``pyproject.toml``.

.. code-block:: bash

    python create_venv.py

.. important :: *dfetch* is primarily developed with python 3.8

Running in Gitpod
-----------------
Gitpod makes it possible to edit dfetch directly in the browser in a VSCode instance.
All dependencies are pre-installed and makes it easy to get started.

|GitpodLink|_

.. |GitpodLink| image:: https://gitpod.io/button/open-in-gitpod.svg
.. _GitpodLink: https://gitpod.io/#https://github.com/dfetch-org/dfetch/


Running in VSCode
-----------------
To debug or run directly from VSCode create the :ref:`virtual environment`.
Select the python from the virtual environment.
And open the ``dfetch.code-workspace``.

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
and add run the ``Feature tests (wip)`` debug configuration in VSCode.


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

    git tag -a '0.5.0' -m "Release version 0.5.0"
    git push --tags

- If all tests ok, create release in the `GitHub webui <https://github.com/dfetch-org/dfetch/releases/new>`_.
- Make sure all dependencies in ``pyproject.toml`` are pinned.
- Copy the CHANGELOG entry of the release to github.
- When the release is created, a new package is automatically pushed to `PyPi <https://pypi.org/project/dfetch/>`_.

- After release, add new header to ``CHANGELOG.rst``:

.. code-block:: rst

    Release 0.0.3 (In development)
    ===================================
