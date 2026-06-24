
.. _patching:

Patch a project
===============

*Dfetch* has a first-class patch workflow.  When you need to fix a bug or
apply a customisation to a vendored dependency, you can track that change as a
patch file that is automatically re-applied on every :ref:`dfetch update
<update>`.  When the fix is ready to share, :ref:`format-patch` converts it
into a contributor-ready unified diff that upstream maintainers can apply
directly.

.. note::

   New to patching with *Dfetch*?  Start with :ref:`first-patch` in the
   getting-started tutorial, which walks through creating and applying
   your first patch step by step.

The full lifecycle looks like this:

1. :ref:`patching-create` — capture local edits as a ``.patch`` file with ``dfetch diff``
2. :ref:`patching-wire` — reference the patch from the manifest so it is applied on every fetch
3. :ref:`patching-update` — refresh the patch as your edits evolve with ``dfetch update-patch``
4. :ref:`patching-upstream-bump` — re-apply your patch when you move to a new upstream version
5. :ref:`patching-upstream` — reformat the patch for upstream use with ``dfetch format-patch``

.. _patching-prereq:

Before you begin
----------------

*Dfetch* calculates the diff for a project by comparing the working tree
against the revision recorded in the project's ``.dfetch_data.yaml`` metadata
file.  For that comparison to be meaningful, the fetched files should already
be committed to your superproject's VCS — they become the baseline that the
patch is measured against.

After fetching, commit before editing:

.. tabs::

   .. tab:: Git

      .. code-block:: console

          $ dfetch update some-project
          $ git add some-project/
          $ git commit -m "vendor: add some-project v1.2.3"

   .. tab:: SVN

      .. code-block:: console

          $ dfetch update some-project
          $ svn add some-project/
          $ svn commit some-project/ -m "vendor: add some-project v1.2.3"

You can then make edits to ``some-project/`` and capture them with
``dfetch diff``.  Both committed and uncommitted edits are included in the
generated patch, so you do not need to commit every intermediate step — only
the clean upstream baseline matters.

.. _patching-create:

Capturing local changes
-----------------------

After fetching a project with :ref:`dfetch update <update>`, make your edits
directly in the vendored source tree.  Once you are happy with the changes,
run:

.. code-block:: console

    $ dfetch diff some-project

*Dfetch* compares the working tree against the revision recorded in the
metadata file and writes a patch file named ``some-project.patch``.

.. asciinema:: ../asciicasts/diff.cast

**What goes into the patch**

The diff captures all tracked modifications and any new untracked files in the
vendored directory.  Files ignored by your superproject's VCS (via
``.gitignore`` or ``svn:ignore``) and the ``dfetch`` metadata file itself are
always excluded.

**Controlling which revisions are compared**

By default, *Dfetch* uses the revision stored in the project's metadata as the
base.  You can override this:

- Single base revision: ``dfetch diff some-project --revs 23864ef2``
- Explicit range: ``dfetch diff some-project --revs 23864ef2:4a9cb18``

See :ref:`diff` in the command reference for all options.

.. tabs::

   .. tab:: Git

      .. scenario-include:: ../features/diff-in-git.feature

   .. tab:: SVN

      .. scenario-include:: ../features/diff-in-svn.feature

.. _patching-wire:

Adding the patch to the manifest
---------------------------------

Once you have a patch file, commit it to your repository and reference it from
the project entry in ``dfetch.yaml`` using the :ref:`patch` attribute:

.. code-block:: yaml

    manifest:
      version: '0.0'
      projects:
        - name: some-project
          url: https://github.com/example/some-project
          tag: v1.2.3
          patch: some-project.patch

From this point on, every ``dfetch update`` will fetch the upstream source and
re-apply the patch on top.  You can test the round-trip immediately:

.. code-block:: console

    $ dfetch update --force some-project

The ``--force`` flag overwrites the working tree with the freshly fetched and
patched version.  Confirm the result looks right, then commit the manifest
change and the patch file together.

**Organizing patch files**

Keep patch files alongside ``dfetch.yaml`` or in a dedicated subdirectory such
as ``patches/``.  *Dfetch* resolves patch paths relative to the manifest file,
so as long as the path in the manifest matches the location on disk you have
full flexibility.  Committing the patch files to VCS ensures every team member
and every CI run gets the same result.

**Multiple patches**

You can split your changes into separate, focused patch files and list them in
order:

.. code-block:: yaml

          patch:
            - 001-fix-null-dereference.patch
            - 002-add-missing-header.patch

Patches are applied in the order listed.  A good convention is to prefix each
file name with a three-digit, zero-padded number (``001-``, ``002-``, …) so
they sort correctly and their purpose is clear at a glance.  The ``dfetch update-patch``
command always updates the **last** patch in the list, so the earlier patches represent
stable, settled changes and the final one accumulates ongoing work.

See :ref:`patch` in the manifest reference for the full attribute syntax.

.. _patching-update:

Refreshing a patch
------------------

As your local edits evolve, the existing patch file may become stale.  Instead
of manually regenerating it, run:

.. code-block:: console

    $ dfetch update-patch some-project

This command:

1. Re-fetches the upstream revision (without applying any patches).
2. Computes the diff between that clean baseline and your current working tree.
3. Overwrites the **last** patch in the manifest list with the new diff.
4. Re-fetches the project and applies all patches so the working tree is left
   in the patched state.

It is safe to run repeatedly as you iterate on a fix.  The upstream revision
stays unchanged — only the patch file is updated.

.. note::

   ``update-patch`` requires the project directory to have **no uncommitted
   changes** in the superproject.  Commit your work first (Git users can also
   ``git stash``), then run the command.

.. asciinema:: ../asciicasts/update-patch.cast

See :ref:`update-patch` in the command reference for all options.

.. tabs::

   .. tab:: Git

      .. scenario-include:: ../features/update-patch-in-git.feature

   .. tab:: SVN

      .. scenario-include:: ../features/update-patch-in-svn.feature

.. _patching-upstream-bump:

Upgrading the upstream version
-------------------------------

When you want to move to a new upstream release, update the ``tag``,
``branch``, or ``revision`` in ``dfetch.yaml`` and then run ``dfetch update``.
*Dfetch* fetches the new version and attempts to re-apply the patch using fuzzy
matching, so patches often survive minor context changes automatically.

.. code-block:: console

    $ # 1. Edit dfetch.yaml: change tag v1.2.3 → v1.3.0
    $ dfetch update some-project

Three outcomes are possible:

**Patch applies cleanly** — you are done.  Review the result, commit the
updated manifest and the updated vendored files.

**Patch applies with fuzz warnings** — the patch applied but the context lines
shifted slightly.  The files are in the correct state.  Run
``dfetch update-patch some-project`` to refresh the patch against the new
baseline so it stays clean for future upgrades:

.. tabs::

   .. tab:: Git

      .. code-block:: console

          $ git add some-project/
          $ git commit -m "vendor: update some-project to v1.3.0"
          $ dfetch update-patch some-project
          $ git add some-project.patch
          $ git commit -m "patches: refresh some-project.patch for v1.3.0"

   .. tab:: SVN

      .. code-block:: console

          $ svn commit some-project/ -m "vendor: update some-project to v1.3.0"
          $ dfetch update-patch some-project
          $ svn commit some-project.patch -m "patches: refresh some-project.patch for v1.3.0"

**Patch fails to apply** — the upstream changes conflict with the local edits
tracked in the patch.  Resolve the conflict manually by editing the vendored
files, then use ``dfetch update-patch`` to record the resolved state:

.. tabs::

   .. tab:: Git

      .. code-block:: console

          $ # Manually resolve conflicts in some-project/
          $ git add some-project/
          $ git commit -m "vendor: update some-project to v1.3.0 with resolved conflicts"
          $ dfetch update-patch some-project
          $ git add some-project.patch
          $ git commit -m "patches: update some-project.patch for v1.3.0"

   .. tab:: SVN

      .. code-block:: console

          $ # Manually resolve conflicts in some-project/
          $ svn commit some-project/ -m "vendor: update some-project to v1.3.0 with resolved conflicts"
          $ dfetch update-patch some-project
          $ svn commit some-project.patch -m "patches: update some-project.patch for v1.3.0"

.. _patching-review:

Replaying patches
-----------------

When you want to understand what a patch (or a set of patches) actually
contributes to a vendored project, run:

.. code-block:: console

    $ dfetch replay-patches some-project

*Dfetch* puts the clean upstream source in the git index and applies the
patches to the working tree.  You can now see exactly what the patches change
using any diff tool you prefer — for example:

.. code-block:: console

    $ git diff some-project/

Or open the project in VS Code and browse the **Changes** view in the Source
Control panel.  (The **Staged Changes** view shows something different and
unrelated to your patches — use **Changes**.)

When you are done, press **Enter** and *dfetch* restores everything to its
original state.

**Replaying a specific number of patches**

Use ``--count`` to stop at a particular patch in the stack.  For example, to
see only what the first patch contributes, with the rest still un-applied:

.. code-block:: console

    $ dfetch replay-patches --count 1 some-project

**Stepping through the stack interactively**

Use ``--interactive`` (or ``-i``) to step through the patch stack one patch at
a time using the ← and → arrow keys.  As you step, the working tree is updated
so your editor always reflects the current position in the stack:

.. code-block:: console

    $ dfetch replay-patches --interactive some-project

Press **Enter** to finish and restore the original state.

.. asciinema:: ../asciicasts/replay-patches.cast

.. tabs::

   .. tab:: Git

      .. scenario-include:: ../features/replay-patches-in-git.feature

   .. tab:: SVN

      .. scenario-include:: ../features/replay-patches-in-svn.feature

.. _patching-upstream:

Contributing the patch upstream
---------------------------------

Patches generated by ``dfetch diff`` are relative to the project's vendored
directory inside your repository.  Most upstream projects expect patches to be
relative to their own root, which is a different path.  To reformat all patches
for a project:

.. code-block:: console

    $ dfetch format-patch some-project

This writes a ``formatted-some-project.patch`` file (or one file per patch if
there are several) in the current directory.  Use ``--output-directory`` to
place the formatted files in a specific location:

.. code-block:: console

    $ dfetch format-patch some-project --output-directory patches/upstream

Before sending a patch, do a dry-run check to confirm it applies cleanly to a
local clone of the upstream repository:

.. tabs::

    .. tab:: Git

        .. code-block:: console

            $ git apply --check formatted-some-project.patch

        .. scenario-include:: ../features/format-patch-in-git.feature

        Once confirmed, hand the file off to the upstream project.  Upstream
        maintainers can apply it with `git am
        <https://git-scm.com/docs/git-am>`_:

        .. code-block:: console

            $ git am formatted-some-project.patch

        Each patch file results in a separate commit.

    .. tab:: SVN

        .. code-block:: console

            $ svn patch formatted-some-project.patch

        .. scenario-include:: ../features/format-patch-in-svn.feature

.. asciinema:: ../asciicasts/format-patch.cast

See :ref:`format-patch` in the command reference for all options.

.. _patching-troubleshooting:

Troubleshooting
---------------

**"No diffs found"**

    ``dfetch diff`` found no changes between the working tree and the upstream
    baseline recorded in ``.dfetch_data.yaml``.  If you expected changes, make
    sure the edits are in the vendored directory and are not excluded by your
    VCS ignore rules.  If the metadata file is missing, run
    ``dfetch update some-project`` first to re-establish the baseline.

**Patch fails to apply after an upstream bump**

    The upstream version introduced changes that conflict with the local edits
    in the patch.  Follow the manual resolution workflow in
    :ref:`patching-upstream-bump`: edit the vendored files to the desired
    state, commit them, then run ``dfetch update-patch`` to regenerate the
    patch from the resolved working tree.

**"skipped - Uncommitted changes"**

    ``dfetch update-patch`` detected uncommitted changes in the project
    directory.  Commit those changes first (Git users can also ``git stash``),
    then run the command so the patch calculation starts from a clean state.

**"skipped - the project was never fetched before"**

    Run ``dfetch update some-project`` first.  The project must exist on disk
    before a patch can be updated.

**"skipped - there is no patch file"**

    The project has no ``patch:`` entry in the manifest.  Use
    ``dfetch diff some-project`` to create the initial patch, then add it to
    the manifest as described in :ref:`patching-wire`.
