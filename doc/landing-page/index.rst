.. Dfetch documentation master file

:sd_hide_title:

.. meta::
   :description: Dfetch vendors source code from Git and SVN repositories directly into your project. No submodules, no lock-in, fully self-contained.
   :keywords: dfetch, dependency management, vendoring, git, svn, embedded development, source-only dependencies, multi-repo, supply chain, sbom, license compliance
   :author: Dfetch Contributors
   :google-site-verification: rXUIdonVCg6XtZUDdOd7fJdSNj3bOoJJRqCFn3OVb04

.. raw:: html

   <meta property="og:title" content="Dfetch — Vendor dependencies without the pain">
   <meta property="og:description" content="VCS-agnostic source-only dependency management. Works with Git and SVN. No submodules, no lock-in, supply-chain ready.">
   <meta property="og:image" content="https://dfetch.rtfd.io/static/dfetch-logo.png">
   <meta property="og:url" content="https://dfetch-org.github.io">

   <meta name="twitter:card" content="summary_large_image">
   <meta name="twitter:title" content="Dfetch — Vendor dependencies without the pain">
   <meta name="twitter:description" content="VCS-agnostic source-only dependency management. Works with Git and SVN. No submodules, no lock-in, supply-chain ready.">
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

:bdg-primary-line:`Git` :bdg-primary-line:`SVN` :bdg-secondary-line:`MIT License` :bdg-success-line:`Zero lock-in` :bdg-info-line:`CI/CD ready` :bdg-warning-line:`Supply-chain safe`


.. div:: band-tint

   :material-regular:`stars;2em;sd-text-primary` **What makes Dfetch different**

   .. grid:: 1 1 3 3
      :gutter: 3

      .. grid-item-card:: :material-regular:`shuffle;2em` Any VCS, mixed freely
         :text-align: center
         :class-card: stat-card

         Works with **Git and SVN** — even mixed in the same project.
         The only dependency manager that bridges both without compromise.

      .. grid-item-card:: :material-regular:`code;2em` Any language, any build system
         :text-align: center
         :class-card: stat-card

         C, C++, Python, Go, Rust, Java — dfetch doesn't care.
         No build-system assumptions. Bring your own toolchain.

      .. grid-item-card:: :material-regular:`history;2em` Built for 15+ year lifecycles
         :text-align: center
         :class-card: stat-card

         Designed for long-lived embedded and industrial products.
         Reproducible builds from source — **no registry, no CDN, no service required**.


.. card::  :material-regular:`done_all;4em;sd-text-primary` **Stay up to date — effortlessly**
   :class-card: sd-bg-dark sd-text-light

   Check which dependencies have available updates and pull them in when you are ready.
   *Dfetch* puts you in control of every change — no surprise breakages, no forced upgrades.

   .. asciinema:: ../asciicasts/check.cast


.. grid:: 1 1 2 2

   .. grid-item::

      :material-regular:`shuffle;4em;sd-text-primary` **VCS-agnostic**

      Works seamlessly with **Git and SVN** — even mixed within the same project.
      Pin by tag, branch, revision, or exact commit hash. Adapt to your team's workflow, not the other way around.


   .. grid-item::

      :material-regular:`archive;4em;sd-text-primary` **Fully self-contained**

      Every dependency is stored **inside your repository** as plain source code.
      No external links means simpler audits, offline builds, and hassle-free deployments that stay reproducible forever.


   .. grid-item::

      :material-regular:`inventory_2;4em;sd-text-primary` **Fetch only what you need**

      Point *Dfetch* at a single subfolder inside a larger repo using the ``src:`` attribute.
      Pull in just the files you need — **no bloat, no noise**, and license files are always retained.


   .. grid-item::

      :material-regular:`lock_open;4em;sd-text-primary` **Zero lock-in**

      Your vendored code stays as plain source files. Switch tools any time — **no proprietary formats, no migration work**.
      *Dfetch* respects that your source code belongs to you.


.. card:: :material-regular:`difference;4em;sd-text-primary` **Customize without losing upstream**
   :class-card: sd-bg-dark sd-text-light

   Vendor a dependency, tweak it locally, and still stay current with upstream — *Dfetch* makes this safe.

   ``dfetch diff`` generates clean patch files from your local modifications.
   On every subsequent update those patches are **re-applied automatically**, keeping your customizations alive
   without forking. When you're ready, upstream the fix properly and drop the patch.


.. card:: :material-regular:`smart_toy;4em;sd-text-primary` **Built for modern CI/CD**
   :class-card: sd-bg-dark sd-text-light

   *Dfetch* plugs right into your automation pipeline. Report dependency update status to
   **GitHub, GitLab, Jenkins, DependencyTrack** and more — keeping your entire team informed, automatically.

   .. asciinema:: ../asciicasts/check-ci.cast


.. div:: band-mint

   :material-regular:`security;2em;sd-text-primary` **Supply-chain ready out of the box**

   .. grid:: 1 1 3 3
      :gutter: 3

      .. grid-item-card:: :material-regular:`receipt_long;2em` SBOM generation
         :text-align: center

         Generate a machine-readable **Software Bill of Materials** to track every vendored dependency —
         ready for audits, compliance checks, and vulnerability scans.

      .. grid-item-card:: :material-regular:`balance;2em` Automatic license detection
         :text-align: center

         Infers and reports the license for every dependency automatically.
         Stay legally compliant — **even when fetching a single subfolder** from a larger repository.

      .. grid-item-card:: :material-regular:`analytics;2em` Multi-format reports
         :text-align: center

         Export to **Jenkins JSON, SARIF, Code Climate, DependencyTrack** formats.
         Plug into your existing security toolchain with zero extra work.


.. card:: :material-regular:`bolt;2em` Already using submodules? Migrate in seconds.

   ``dfetch import`` automatically converts **Git submodules and SVN externals** into a dfetch manifest.
   No manual work, no lost history — start benefiting from dfetch's workflow immediately.

   .. button-link:: https://dfetch.rtfd.io/en/latest/manual.html#import
      :color: primary
      :shadow:

      :material-regular:`description;1.2em` Read the migration guide


.. card:: :material-regular:`description;1.5em` Example ``dfetch.yaml``

   .. literalinclude:: ../../dfetch.yaml
      :language: yaml


.. div:: sd-text-left sd-text-muted sd-font-weight-light

    Generated: |today|
