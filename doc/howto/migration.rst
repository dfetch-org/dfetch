
.. _migration:

Migrate to Dfetch
=================

*Dfetch* can convert an existing project that uses Git submodules or SVN
externals into a Dfetch-managed project.  The :ref:`dfetch import <import>`
command reads your current dependency configuration and writes a
:ref:`Manifest` — after that you remove the old mechanism and let
:ref:`dfetch update <update>` take over.

Choose the guide that matches your current setup:

- :ref:`migration-git`
- :ref:`migration-svn`

.. _migration-git:

From Git submodules
-------------------

**Before you start**, make sure:

- Your repository is fully up-to-date (``git pull``).
- All submodules are initialised and checked out:

  .. code-block:: console

      $ git submodule update --init --recursive

**Steps**

1. Generate a manifest from the existing submodules:

   .. code-block:: console

       $ dfetch import

   This writes a ``dfetch.yaml`` file in the current directory listing each
   submodule as a *Dfetch* project entry, pinned to the commit that is
   currently checked out.

2. Remove all Git submodules.  For each submodule (replace ``<path>`` with
   the submodule path, e.g. ``ext/mylib``):

   .. code-block:: console

       $ git submodule deinit -f <path>
       $ git rm -f <path>
       $ rm -rf .git/modules/<path>

   Repeat until ``git submodule status`` returns nothing.  Commit the
   result:

   .. code-block:: console

       $ git commit -m "chore: remove git submodules (switching to Dfetch)"

   .. seealso::

      `How do I remove a submodule?
      <https://stackoverflow.com/questions/1260748/>`_

3. Fetch all projects into your repository:

   .. code-block:: console

       $ dfetch update

4. Commit the fetched files:

   .. code-block:: console

       $ git add .
       $ git commit -m "chore: vendor dependencies with Dfetch"

.. scenario-include:: ../features/import-from-git.feature

.. _migration-git-branches:

Switching branches after migration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you migrate on a feature branch while ``master`` still has the original
submodules, you will run into a few rough edges when switching back and
forth.

**From submodule branch → manifest branch**

Git will refuse to check out if a *Dfetched* dependency would overwrite a
submodule directory that is still in place:

.. code-block:: console

    $ git checkout feature/use-dfetch
    error: The following untracked working tree files would be overwritten by checkout:
        MySubmodule/somefile.c
        MySubmodule/someotherfile.c

``git status`` shows a clean tree — the files belong to the submodule, which
Git does not track as ordinary working-tree files.

To work around this, delete the directory before switching:

.. code-block:: console

    $ rm -rf MySubmodule
    $ git checkout feature/use-dfetch

If you have several submodules, remove them all before checking out.

**From manifest branch → submodule branch**

This direction succeeds without errors, but Git leaves the submodule
directories empty.  After checking out, re-initialise them:

.. code-block:: console

    $ git checkout master
    $ git submodule update --init --recursive
    Submodule path 'MySubmodule': checked out '08f95e01b297d8b8c1c9101bde58e75cd4d428ce'

.. _migration-svn:

From SVN externals
------------------

**Before you start**, make sure your working copy is fully up-to-date:

.. code-block:: console

    $ svn update

**Steps**

1. Generate a manifest from the existing externals:

   .. code-block:: console

       $ dfetch import

   This writes a ``dfetch.yaml`` listing every ``svn:externals`` entry as a
   *Dfetch* project, pinned to the revision that is currently set.

2. Remove all SVN externals.  Externals are stored as a property on a
   directory — you need to delete that property for every directory that has
   one.

   List all directories with ``svn:externals`` set:

   .. code-block:: console

       $ svn proplist -R | grep -B1 svn:externals

   For each such directory (replace ``<directory>``):

   .. code-block:: console

       $ svn propdel svn:externals <directory>

   Commit the property removal:

   .. code-block:: console

       $ svn commit -m "Remove SVN externals (switching to Dfetch)"

   .. seealso::

      `How do I remove SVN externals?
      <https://stackoverflow.com/questions/1044649/>`_

   .. note::

      If your externals contain nested externals, ``dfetch import`` only
      reads the top-level ``svn:externals`` property.  Run ``dfetch import``
      inside each nested external directory and merge the resulting entries
      into your top-level ``dfetch.yaml`` by hand.

3. Fetch all projects into your working copy:

   .. code-block:: console

       $ dfetch update

4. Commit the fetched files:

   .. code-block:: console

       $ svn add --force .
       $ svn commit -m "Vendor dependencies with Dfetch"

.. scenario-include:: ../features/import-from-svn.feature
