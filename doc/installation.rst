


Installation
============

From pip
--------

If you are using python you can install the latest release with:

.. code-block:: bash

   pip install dfetch

Or install the latest version from the main branch:

.. code-block:: bash

   pip install git+https://github.com/dfetch-org/dfetch.git#egg=dfetch

Binary distributions
--------------------

Each release on the `releases page <https://github.com/dfetch-org/dfetch/releases>`_
provides pre-built installers for all major platforms, so no compilation is required.

Each installer package has a name in the format ``<version>-<platform>``.

- ``<version>`` shows the software version:

    - If it includes ``dev``, it is a development release (for testing).
    - If it is only numbers (e.g. ``0.11.0``), it is an official release.

- ``<platform>`` indicates the system the installer is for: ``nix`` (Linux), ``osx`` (Mac), or ``win`` (Windows).

The version is automatically determined from the project and used to name the installer files.

.. tabs::

    .. tab:: Linux

        Download the  ``.deb`` or ``.rpm`` package from the releases page and install it.

        Debian / Ubuntu (``.deb``):

        .. code-block:: bash

            sudo dpkg -i dfetch-<version>-nix.deb

        RPM-based distributions (``.rpm``):

        .. code-block:: bash

            sudo dnf install dfetch-<version>-nix.rpm
            # or
            sudo rpm -i dfetch-<version>-nix.rpm

    .. tab:: macOS

        Download the ``.pkg`` package from the releases page and install it.

        .. code-block:: bash

            sudo installer -pkg dfetch-<version>-osx.pkg -target /

    .. tab:: Windows

        Download the ``.msi`` installer and install by double-clicking or use:

        .. code-block:: powershell

            msiexec /i dfetch-<version>-win.msi

        Uninstalling can be done through the regular Add/Remove programs section.

Validating Installation
-----------------------

Run the following command to verify the installation

.. code-block:: bash

    dfetch environment

.. asciinema:: asciicasts/environment.cast
