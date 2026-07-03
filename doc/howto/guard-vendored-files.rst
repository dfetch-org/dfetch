.. _guard-vendored-files:

Guard vendored files
====================

Files fetched by *Dfetch* are plain files in your repository, so your formatters,
linters and teammates can touch them just like any other file. Local changes to
vendored files are overwritten on the next ``dfetch update``, so it pays to keep
tools away from them. ``dfetch filter`` gives you the list of paths that *Dfetch*
manages, making this easy to automate.

Skip vendored files when running a tool
---------------------------------------

Put the tool and its arguments after ``dfetch filter --not-dfetched`` and the tool
is called with only the paths that are yours:

.. code-block:: console

    $ dfetch filter --not-dfetched black src/main.py third-party/mymodule/module.py

Here ``black`` formats ``src/main.py`` only, since ``third-party/mymodule`` is a
project destination in the manifest. Arguments that aren't existing paths (such as
``--check``) are passed to the tool untouched.

Use it as a pre-commit hook
---------------------------

In a `pre-commit <https://pre-commit.com>`_ configuration, set ``dfetch`` as the
entry and put the tool in the arguments. The staged file names that pre-commit
appends are then filtered before the tool runs:

.. code-block:: yaml

    repos:
    -   repo: local
        hooks:
        -   id: black
            name: Black (auto-format)
            entry: dfetch
            args: ['filter', '--not-dfetched', 'black']
            language: system
            types: [file, python]

This replaces manually maintained ``exclude:`` patterns: whenever you add a project
to the manifest, the hook automatically skips its destination. *Dfetch* uses this
in its own `pre-commit configuration
<https://github.com/dfetch-org/dfetch/blob/main/.pre-commit-config.yaml>`_.

List or check vendored files
----------------------------

Without a wrapped command, ``dfetch filter`` prints the filtered paths, one per
line, ready for further scripting:

.. code-block:: console

    $ git diff --name-only | dfetch filter
    third-party/mymodule/module.py

For example, you can let a CI step fail when a changeset touches vendored files:

.. code-block:: bash

    test -z "$(git diff --name-only origin/main... | dfetch filter)"

See the :doc:`command reference </reference/commands>` for all options of ``dfetch filter``.
