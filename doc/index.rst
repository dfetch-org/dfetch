

.. meta::
   :description: Dfetch vendors source code from Git or SVN repositories or plain archives directly
                 into your project. No submodules, no lock-in, fully self-contained. Supply-chain ready.
   :keywords: dfetch, dependency management, vendoring, git, svn, archive, embedded development, source-only dependencies, multi-repo, supply chain, sbom, license compliance
   :author: Dfetch Contributors
   :google-site-verification: yCnoTogJMh7Nm5gxlREDuONIXT4ijHcj972Y5k9p-sU

.. raw:: html

   <meta property="og:title" content="Dfetch — Vendor dependencies without the pain">
   <meta property="og:description" content="VCS-agnostic source-only dependency management. Works with Git and SVN. No submodules, no lock-in, supply-chain ready.">
   <meta property="og:image" content="https://dfetch.rtfd.io/static/dfetch-logo.png">
   <meta property="og:url" content="https://dfetch.rtfd.io">

   <meta name="twitter:card" content="summary_large_image">
   <meta name="twitter:title" content="Dfetch — Vendor dependencies without the pain">
   <meta name="twitter:description" content="VCS-agnostic source-only dependency management. Works with Git and SVN. No submodules, no lock-in, supply-chain ready.">
   <meta name="twitter:image" content="https://dfetch.rtfd.io/static/dfetch-logo.png">


.. image:: images/dfetch_header.png
   :width: 100%
   :align: center

Dfetch — *vendor dependencies without the pain*
================================================

**Dfetch** copies source code directly into your project — no Git submodules, no SVN externals,
no hidden external links. Fetch from Git, SVN, or plain archive URLs. Dependencies live as plain,
readable files inside your own repository. You stay in full control of every line.

Dfetch is supply-chain ready out of the box: generate SBOMs, detect licenses, and export
reports for Jenkins, SARIF, and Code Climate. Apply local patches and keep them syncable with
upstream. See :ref:`vendoring` for background on the problem this solves.

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
