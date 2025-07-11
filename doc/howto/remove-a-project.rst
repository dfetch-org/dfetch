.. _remove-a-project:

Remove a project
================

``dfetch remove`` deletes a project from your manifest and removes its
directory from disk. Use it when you no longer need a dependency.

- :ref:`removing-basic` — remove a single project
- :ref:`removing-multiple` — remove several projects at once
- :ref:`removing-backup` — manifest backup behavior

.. _removing-basic:

Removing a single project
-------------------------

Pass the project name to ``dfetch remove``:

.. code-block:: console

    $ dfetch remove mylib

*Dfetch* removes the project entry from ``dfetch.yaml`` and deletes the
destination folder. The manifest is updated in-place when inside a Git or
SVN repository, preserving comments and formatting. Outside version control,
a ``.backup`` copy is created first.

.. scenario-include:: ../features/remove-project.feature

.. _removing-multiple:

Removing multiple projects
--------------------------

List multiple project names to remove them all at once:

.. code-block:: console

    $ dfetch remove lib1 lib2 lib3

Each project is removed from the manifest and its directory deleted.

.. asciinema:: ../asciicasts/remove.cast

.. _removing-backup:

Manifest backup behavior
------------------------

When your manifest lives inside a Git or SVN repository, ``dfetch remove``
edits it in-place to preserve comments, blank lines, and indentation. When
outside version control (no ``.git`` or ``.svn`` directory), a backup copy
is created as ``dfetch.yaml.backup`` before any changes.

This matches the behavior of ``dfetch freeze`` and other manifest-modifying
commands.
