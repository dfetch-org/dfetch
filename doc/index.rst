

.. meta::
   :description: Dfetch is a VCS-agnostic tool that simplifies dependency management by retrieving
                 source-only dependencies from various repositories, promoting upstream changes and
                 allowing local customizations.
   :keywords: dfetch, dependency management, embedded development, fetch tool, vendoring, multi-repo, dependencies, git, svn, package manager, multi-project, monorepo
   :author: Dfetch Contributors
   :google-site-verification: yCnoTogJMh7Nm5gxlREDuONIXT4ijHcj972Y5k9p-sU

.. raw:: html

   <meta property="og:title" content="Dfetch - a source-only no-hassle project-dependency aggregator">
   <meta property="og:description" content="VCS-agnostic tool to simplify using source-only dependencies of multiple repositories.">
   <meta property="og:image" content="https://dfetch.rtfd.io/static/dfetch-logo.png">
   <meta property="og:url" content="https://dfetch.rtfd.io">

   <meta name="twitter:card" content="summary_large_image">
   <meta name="twitter:title" content="Dfetch - a source-only no-hassle project-dependency aggregator">
   <meta name="twitter:description" content="VCS-agnostic tool to simplify using source-only dependencies of multiple repositories.">
   <meta name="twitter:image" content="https://dfetch.rtfd.io/static/dfetch-logo.png">


.. image:: images/dfetch_header.png
   :width: 100%
   :align: center

Dfetch — *a source-only no-hassle project-dependency aggregator*
================================================================

We make products that can last 15+ years; because of this we want to be able to have all sources
available to build the entire project from source without depending on external resources.
For this, we needed a dependency manager flexible enough to retrieve dependencies as plain text
from various sources. `svn externals`, `git submodules` and `git subtrees` solve a similar
problem, but not in a VCS-agnostic or completely user-friendly way.
Dfetch must promote upstreaming changes, but allow for local customisations.
See :ref:`vendoring` for background on why this matters.

.. asciinema:: asciicasts/basic.cast

----

.. toctree::
   :maxdepth: 2
   :caption: Tutorials

   installation
   getting_started

.. toctree::
   :maxdepth: 2
   :caption: How-to Guides

   troubleshooting
   contributing

.. toctree::
   :maxdepth: 2
   :caption: Reference

   manifest
   manual
   changelog
   legal

.. toctree::
   :maxdepth: 2
   :caption: Explanation

   vendoring
   alternatives
   internal
