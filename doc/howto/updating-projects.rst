
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

.. _updating-line-endings:

Line endings
------------

If your superproject is a git repository and its ``.gitattributes`` file
contains a global or per-directory ``eol`` rule, *DFetch* lets the version
control system that performs the fetch produce matching line endings, so the
vendored files match your project's enforced style on every platform:

.. code-block:: text

   # force LF everywhere (common on cross-platform projects)
   * text=auto eol=lf

   # force CRLF everywhere (less common, but valid)
   * text=auto eol=crlf

*DFetch* uses ``git check-attr`` to resolve the effective setting for each
dependency's destination directory, so per-directory rules are honoured as
well as global ones. The conversion itself is done natively by the VCS that
fetches the project, so even large dependencies convert at full speed:

- Git dependencies are checked out with the requested ``eol`` configured and
  renormalised by git itself; git's own text detection decides which files
  are text, so binary files are never converted.
- SVN dependencies are exported with ``svn export --native-eol``, which
  applies the requested ending to every file carrying the
  ``svn:eol-style=native`` property; files without that property keep their
  bytes exactly as stored.

If your superproject is an SVN repository, declare the preference with SVN's
own mechanism instead — the ``svn:auto-props`` property:

.. code-block:: console

   svn propset svn:auto-props '* = svn:eol-style=LF' .

*DFetch* reads the property (including values inherited from parent
directories) for each dependency's destination and applies it the same way.

Archive dependencies are extracted byte-for-byte. If no preference is set,
the platform and VCS defaults apply unchanged.

The scenarios below cover both Git and SVN subprojects, and verify all four
combinations of remote content (LF or CRLF) against each superproject
``eol`` setting — expressed concisely via Gherkin ``Examples`` tables. They
also verify that a superproject using another VCS (such as SVN) leaves the
fetched line endings untouched:

.. scenario-include:: ../features/superproject-line-ending-attrs.feature
