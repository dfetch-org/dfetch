.. Dfetch documentation master file

Dfetch
======
.. warning:: Dfetch is in a proof-of-concept state and will have breaking changes!

.. toctree::
   :maxdepth: 3
   :caption: Contents:

   getting_started
   manifest
   manual
   command-line


What is Dfetch?
---------------

Dfetch is source-only no-hassle project-dependency aggregator.

We needed a dependency manager that was flexible enough to retrieve dependencies as plain text
from various sources. `svn externals`, `git submodules` and `git subtrees` solve a similar
problem, but not in a vcs agnostic way or completely user friendly way.
We want self-contained code repositories without any hassle for end-users.
Dfetch must promote upstreaming changes, but allow for local customizations.

Other tools that do similar things are ``Zephyr's West``, ``CMake ExternalProject`` and other meta tools.

Installation
------------
`Dfetch` is a python based cross-platform cli tool.
To install it either install the python package or download the binary and place it in your system PATH.

.. code-block::

   dfetch --version

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

