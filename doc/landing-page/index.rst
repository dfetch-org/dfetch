.. Dfetch documentation master file

.. image:: ../images/dfetch_header.png
   :height: 203
   :width: 571
   :align: center

.. asciinema:: ../asciicasts/basic.cast


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
