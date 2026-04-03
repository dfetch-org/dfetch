
.. _updating-projects:

Update projects
===============

``dfetch update`` fetches every dependency listed in ``dfetch.yaml`` and
places the requested version in its destination folder.  VCS type (Git, SVN,
or plain archive) is detected automatically.

- :ref:`updating-basic` — fetch all projects at once
- :ref:`updating-selective` — update a single project
- :ref:`updating-force` — overwrite local changes
- :ref:`updating-sub-manifests` — nested manifests in dependencies
- :ref:`updating-submodules` — Git submodules inside dependencies

.. _updating-basic:

Fetching all projects
---------------------

Run without arguments to fetch every project in the manifest:

.. code-block:: console

    $ dfetch update

.. asciinema:: ../asciicasts/update.cast

*Dfetch* reads ``dfetch.yaml``, resolves each project's VCS type, and writes
the requested revision into the destination folder.  A ``.dfetch_data.yaml``
metadata file is created inside each destination so *Dfetch* can track what
version is present.

.. tabs::

   .. tab:: Git

      .. scenario-include:: ../features/fetch-git-repo.feature

   .. tab:: SVN

      .. scenario-include:: ../features/fetch-svn-repo.feature

   .. tab:: Archive

      .. scenario-include:: ../features/fetch-archive.feature

.. _updating-selective:

Updating a single project
--------------------------

Pass one or more project names to limit which entries are updated:

.. code-block:: console

    $ dfetch update mylib

.. code-block:: console

    $ dfetch update mylib myother

.. _updating-force:

Overwriting local changes
--------------------------

By default *Dfetch* skips a project that is already at the requested version
or that has local modifications.  Use ``--force`` (``-f``) to re-fetch and
overwrite regardless:

.. code-block:: console

    $ dfetch update --force mylib

.. warning::

    Any unsaved local edits in the destination directory will be lost.
    Capture them first with ``dfetch diff`` — see :ref:`patching` for the
    full patch workflow.

.. _updating-sub-manifests:

Sub-manifests
--------------

A fetched project may itself contain a ``dfetch.yaml``.  *Dfetch* reads it
after fetching and reports any further dependencies it finds, so you can
decide whether to vendor those as well.

To skip this check entirely:

.. code-block:: console

    $ dfetch update --no-recommendations

.. scenario-include:: ../features/updated-project-has-dependencies.feature

.. _updating-submodules:

Git submodules
---------------

When a Git dependency contains submodules, *Dfetch* fetches and resolves them
automatically — no extra manifest entries or ``git submodule`` commands are
needed.  Each submodule is checked out at the exact revision pinned by the
parent repository.

.. code-block:: console

    $ dfetch update

    Dfetch (0.13.0)
    my-project:
    > Found & fetched submodule "./ext/vendor-lib"  (https://github.com/example/vendor-lib @ master - 79698c9…)
    > Fetched master - e1fda19…

Nested submodules are resolved recursively.  Pinned details for each
submodule are recorded in ``.dfetch_data.yaml`` and are visible in
:ref:`Report`.

.. scenario-include:: ../features/fetch-git-repo-with-submodule.feature
