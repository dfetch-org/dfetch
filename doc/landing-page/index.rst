.. Dfetch documentation master file

:sd_hide_title:

.. meta::
   :description: Dfetch vendors source code from Git and SVN repositories directly into your project. No submodules, no lock-in, fully self-contained.
   :keywords: dfetch, dependency management, vendoring, git, svn, embedded development, source-only dependencies, multi-repo
   :author: Dfetch Contributors
   :google-site-verification: rXUIdonVCg6XtZUDdOd7fJdSNj3bOoJJRqCFn3OVb04

.. raw:: html

   <meta property="og:title" content="Dfetch — Vendor dependencies without the pain">
   <meta property="og:description" content="VCS-agnostic source-only dependency management. Works with Git and SVN. No submodules, no lock-in.">
   <meta property="og:image" content="https://dfetch.rtfd.io/static/dfetch-logo.png">
   <meta property="og:url" content="https://dfetch-org.github.io">

   <meta name="twitter:card" content="summary_large_image">
   <meta name="twitter:title" content="Dfetch — Vendor dependencies without the pain">
   <meta name="twitter:description" content="VCS-agnostic source-only dependency management. Works with Git and SVN. No submodules, no lock-in.">
   <meta name="twitter:image" content="https://dfetch.rtfd.io/static/dfetch-logo.png">

.. image:: ../images/dfetch_header.png
   :width: 100%
   :align: center


Dfetch
######

.. grid:: 3

    .. grid-item::

      .. button-link:: https://pypi.org/project/dfetch/
         :color: primary
         :shadow:
         :expand:

         :material-regular:`download;2em` Download

    .. grid-item::

      .. button-link:: https://dfetch.rtfd.io/
         :color: secondary
         :shadow:
         :expand:

         :material-regular:`description;2em` Docs

    .. grid-item::

      .. button-link:: https://github.com/dfetch-org/dfetch/
         :color: secondary
         :shadow:
         :expand:

         :material-regular:`article;2em` Source

.. asciinema:: ../asciicasts/basic.cast

**Dfetch** vendors source code directly into your project — no Git submodules, no SVN externals, no hidden external links.
Dependencies live as plain, readable files inside your own repository. You stay in full control of every line.

:bdg-primary-line:`Git` :bdg-primary-line:`SVN` :bdg-secondary-line:`MIT License` :bdg-success-line:`Zero lock-in` :bdg-info-line:`CI/CD ready`

.. card::  :material-regular:`done_all;4em;sd-text-primary` **Stay up to date — effortlessly**
   :class-card: sd-bg-dark sd-text-light

   Check which dependencies have available updates and pull them in when you are ready.
   *Dfetch* puts you in control of every change — no surprise breakages, no forced upgrades.

   .. asciinema:: ../asciicasts/check.cast


.. grid:: 1 1 2 2

   .. grid-item::

      :material-regular:`shuffle;4em;sd-text-primary` **VCS-agnostic**

      Works seamlessly with **Git and SVN** — even mixed within the same project. Adapt to your team's workflow, not the other way around.


   .. grid-item::

      :material-regular:`archive;4em;sd-text-primary` **Fully self-contained**

      Every dependency is stored **inside your repository** as plain source code. No external links means simpler audits and hassle-free deployments.


   .. grid-item::

      :material-regular:`build;4em;sd-text-primary` **One YAML file**

      Declare every dependency in a **single readable manifest**. Easy to review in pull requests, trivial to onboard new team members.


   .. grid-item::

      :material-regular:`lock_open;4em;sd-text-primary` **Zero lock-in**

      Your vendored code stays as plain source files. Switch tools any time — **no proprietary formats, no migration work**.


.. card:: :material-regular:`smart_toy;4em;sd-text-primary` **Built for modern CI/CD**
   :class-card: sd-bg-dark sd-text-light

   *Dfetch* plugs right into your automation pipeline. Report dependency update status to
   **GitHub, GitLab, Jenkins, DependencyTrack** and more — keeping your entire team informed, automatically.

   .. asciinema:: ../asciicasts/check-ci.cast


.. card:: :material-regular:`description;1.5em` Example ``dfetch.yaml``

   .. literalinclude:: ../../dfetch.yaml
      :language: yaml


.. div:: sd-text-left sd-text-muted sd-font-weight-light

    Generated: |today|
