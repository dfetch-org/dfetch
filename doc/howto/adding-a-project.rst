
.. _adding-a-project:

Add a project
=============

There are three ways to add a new dependency to your manifest — edit it
directly, use the ``dfetch add`` command, or use the interactive wizard
``dfetch add -i``.

- :ref:`adding-manifest` — write the entry by hand for full control
- :ref:`adding-add` — one command, no prompts
- :ref:`adding-interactive` — guided wizard with branch/tag browsing

.. _adding-manifest:

Editing the manifest directly
------------------------------

Open ``dfetch.yaml`` and add a new entry under ``projects``.  At minimum you
need a ``name`` and a ``url``:

.. code-block:: yaml

    manifest:
      version: '0.0'
      projects:
        - name: mylib
          url: https://github.com/example/mylib.git

Pin to a tag or branch with ``tag`` or ``branch``:

.. code-block:: yaml

    manifest:
      version: '0.0'
      projects:
        - name: mylib
          url: https://github.com/example/mylib.git
          tag: v1.2.3

        - name: myother
          url: https://github.com/example/myother.git
          branch: main
          dst: ext/myother       # optional destination folder

After saving the file, run ``dfetch update`` to fetch the new dependency.
See :ref:`Manifest` for the full list of project attributes.

.. _adding-add:

Using ``dfetch add``
---------------------

Pass the repository URL to ``dfetch add`` and it will append a new entry to
``dfetch.yaml`` without any prompts.  *Dfetch* fetches remote metadata
(branches and tags), selects the default branch, and guesses a destination
path based on your existing projects.

.. code-block:: console

  $ dfetch add https://github.com/some-org/some-repo.git

.. asciinema:: ../asciicasts/add.cast

Override individual fields with flags:

.. code-block:: console

  $ dfetch add \
      --name mylib \
      --dst ext/mylib \
      --version v2.0 \
      --src lib \
      https://github.com/some-org/some-repo.git

After ``dfetch add`` finishes, run ``dfetch update`` to fetch the newly added
project.

.. _adding-interactive:

Using ``dfetch add -i`` (interactive wizard)
--------------------------------------------

The ``--interactive`` (``-i``) flag starts a step-by-step wizard.  Use it
when you want to browse available branches and tags, choose a sub-directory
inside the remote repository, or configure which paths to ignore.

.. code-block:: console

  $ dfetch add -i https://github.com/some-org/some-repo.git

.. asciinema:: ../asciicasts/interactive-add.cast

The wizard walks through each field in turn:

* **name** — defaults to the repository name from the URL
* **dst** — local destination folder; defaults to a path guessed from your
  existing projects
* **version** — scrollable list of all remote branches and tags (arrow keys
  to navigate, Enter to select, Esc to fall back to free-text input)
* **src** — optional sub-path inside the remote; browse the remote tree with
  arrow keys and expand/collapse folders with Enter/Right/Left
* **ignore** — optional paths to exclude; use Space to toggle multiple
  entries and Enter to confirm

You can pre-fill any field to skip its prompt:

.. code-block:: console

  $ dfetch add -i --version main \
                  --src lib/core \
                  https://github.com/some-org/some-repo.git

After you confirm the settings the wizard offers to run ``dfetch update``
immediately so the new project is fetched right away.
