.. Dfetch documentation master file

.. image:: images/dfetch_header.png
   :width: 100%
   :align: center

.. toctree::
   :maxdepth: 2

   getting_started
   manifest
   manual
   troubleshooting
   contributing
   changelog
   alternatives
   legal
   internal

Dfetch
======

What is Dfetch?
---------------

**Dfetch is source-only no-hassle project-dependency aggregator.**

We needed a dependency manager that was flexible enough to retrieve dependencies as plain text
from various sources. `svn externals`, `git submodules` and `git subtrees` solve a similar
problem, but not in a vcs agnostic way or completely user friendly way.
We want self-contained code repositories without any hassle for end-users.
Dfetch must promote upstreaming changes, but allow for local customizations.

Other tools that do similar things are `Zephyr's West`, `CMake ExternalProject` and other meta tools.
See :ref:`alternatives` for a complete list.

Installation
------------
`Dfetch` is a python based cross-platform cli tool.

Install the latest release with:

.. code-block::

   pip install dfetch

Or install the latest version from the main branch:

.. code-block::

   pip install https://github.com/dfetch-org/dfetch/archive/main.zip

Once installed dfetch output can be seen.

.. code-block::

   dfetch --version

Basic usage
-----------

.. asciinema:: asciicasts/basic.cast
