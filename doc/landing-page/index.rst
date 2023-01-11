.. Dfetch documentation master file

:sd_hide_title:

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

Are you tired of managing dependencies using Git submodules or SVN externals? Introducing *Dfetch*, a VCS agnostic, no-hassle, source-only solution
that allows you to easily retrieve dependencies as plain text from various sources. *Dfetch* eliminates the need for Git submodules or SVN externals
by providing a efficient and user-friendly way to manage your project's dependencies using *vendoring*. It promotes upstreaming changes and allows for local
customizations all while maintaining self-contained code repositories.

Say goodbye to the hassle of traditional dependency management solutions and hello to a more efficient and streamlined process with *Dfetch*.

.. card::  :material-regular:`done_all;4em;sd-text-primary` **Check for updates**
   :class-card: sd-bg-dark sd-text-light

   *Dfetch* simplifies dependency management by allowing users to easily check for
   updates and integrate them seamlessly into their codebase.

   .. asciinema:: ../asciicasts/check.cast


.. grid:: 1 1 2 2

   .. grid-item::

      :material-regular:`shuffle;4em;sd-text-primary` **VCS-agnostic**

      *Dfetch* is a versatile solution, being VCS agnostic it can be used with both Git and SVN, enabling users to seamlessly manage dependencies regardless of their VCS of choice and even to mix them.


   .. grid-item::

      :material-regular:`archive;4em;sd-text-primary` **Self-contained**

      *Dfetch* ensures self-contained repositories by including dependencies directly within the project, eliminating external links and making deployment easier.


   .. grid-item::

      :material-regular:`build;4em;sd-text-primary` **Simple yaml config**

      *Dfetch* simplifies configuration with its easy-to-use YAML file, allowing users to set up and manage dependencies with minimal setup and effort.


   .. grid-item::

      :material-regular:`lock_open;4em;sd-text-primary` **No lock-in**

      *Dfetch* provides freedom of choice, users are not locked into using *Dfetch*, they can easily switch to other dependency management solutions.


.. card:: :material-regular:`smart_toy;4em;sd-text-primary` **Integrate**
   :class-card: sd-bg-dark sd-text-light

         *Dfetch* streamlines the integration process by being easily adaptable to various CI/CD automated tools, making it a breeze to implement in any development workflow.
         It can generate reports for Github, Gitlab, Jenkins, DependencyTrack and more!

         .. asciinema:: ../asciicasts/check-ci.cast


.. card:: Example config

   .. literalinclude:: ../../dfetch.yaml
      :language: yaml
