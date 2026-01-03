

Getting Started
===============

Main concepts
-------------
Your project depends on other projects to build or run. In order keep the dependencies
with your project. *Dfetch* can fetch these dependencies and place them with your code.

*Dfetch* starts from a :ref:`Manifest` file. This contains all the :ref:`Projects`
this project is depending on. You as a user can then let *Dfetch* :ref:`update`
your dependencies.

*Dfetch* will fetch the correct version of your dependencies and place them in the
location of your choice. If the folder already exists and the version was updated
*Dfetch* will overwrite the folder with the changes.

Since the version control information (`.git` or `svn`) is removed, *Dfetch* stores some
general information about the project in a `.dfetch_data.yaml` file inside the fetched project.

You can then review the changes in your favorite version control system and commit
the changes as you please.

My first manifest
-----------------
For a complete description of the manifest, see :ref:`Manifest`.

*Dfetch* can generate a basic manifest as starting point with :ref:`dfetch init <init>`.
Alternatively, *Dfetch* can generate a manifest based on the git submodules or svn externals
in an existing project using :ref:`dfetch import <import>`.

Below manifest will retrieve the given tag of *mymodule* from the url listed.
For more options such as ``branch`` and ``revision`` see :ref:`Manifest`.

.. code-block:: yaml

    manifest:
      version: '0.0'

      projects:
        - name: ext/test-repo-tag
          tag: v1
          url: https://github.com/dfetch-org/test-repo

My first update
---------------
After creating the manifest we can let *Dfetch* perform an update.
Make sure that you have installed *Dfetch* as described in :ref:`Installation`.

From a command-line perform the following command::

   dfetch update

*Dfetch* will search through all directories down until it finds the ``dfetch.yaml``
manifest and it will perform the update.

After *Dfetch* finishes, the version of the dependency as listed in your manifest is
downloaded at the target location. You can now commit it to your version control system.

Inside the project folder, *Dfetch* will add a metadata file ``.dfetch_data.yaml``
containing information needed for knowing what version is present.
*Dfetch* can function perfectly without this file, but since it will have no knowledge
of the current contents, updates will always just blindly update.

My first version change
-----------------------
During development of your project you can periodically check for update with.

.. code-block:: console

  dfetch check

*Dfetch* will check for each project if a newer version is available.

.. code-block:: console

  Dfetch (0.5.1)
    ext/test-repo-tag   : wanted & current (v1), available (v2.0)

As can be seen a newer tag is available. If you want to update,
you can manually update the tag of the project in the manifest.

.. note:: If you only have a branch specified, *Dfetch* will update automatically.

.. code-block:: yaml

  manifest:
    version: '0.0'

    projects:
      - name: ext/test-repo-tag
        url: https://github.com/dfetch-org/test-repo
        tag: v2.0

And after that rerunning `update`:

.. code-block:: console

   dfetch update

Now you can review the changes and commit them once again if you are happy.

My first remote
---------------
Typically your project will have multiple dependencies. For instance take the below manifest.

.. code-block:: yaml

  manifest:
    version: '0.0'

    projects:
      - name: ext/test-repo-tag
        url: https://github.com/dfetch-org/test-repo

      - name: cpputest
        url: https://github.com/cpputest/cpputest

Both projects have a very similar url. To simplify your manifest,
it is possible to create a single remote with the common part of the URL (``url-base``).
Below manifest is completely equivalent to the manifest above. For more
details on working with remotes see :ref:`Remotes`.

.. code-block:: yaml

  manifest:
    version: '0.0'

    remotes:
      - name: github
        url-base: https://github.com/

    projects:
      - name: ext/test-repo-tag
        repo-path: dfetch-org/test-repo

      - name: cpputest
        repo-path: cpputest/cpputest

.. scenario-include:: ../features/journey-basic-usage.feature

My first patch
-----------------
Sometimes you need to patch a dependency to get it working with your project.
*Dfetch* supports creating and applying patches after fetching the dependency.

Given you have fetched ``dfetch-org/test-repo`` and you need to apply a patch.
First commit the fetched version to your version control system. This provides
*Dfetch* a reference point.

.. code-block:: console

  git add ext/test-repo-tag
  git commit -m "Add test-repo-tag v2.0"

Then you can work on the files inside ``ext/test-repo-tag``, once you are happy
you can run ``dfetch diff`` to create a patch file with respect to the committed
version.

.. code-block:: console

  dfetch diff

A patch file ``ext-test-repo-tag.patch`` is created in the current folder. You can
place it anywhere you want, as long as it is reachable when running *Dfetch*.
For this example we keep it in the current folder. This patch file can now be applied
automatically by *Dfetch* in next updates. Add it to your manifest as shown below.

.. code-block:: yaml

  manifest:
    version: '0.0'

    remotes:
      - name: github
        url-base: https://github.com/

    projects:
      - name: ext/test-repo-tag
        repo-path: dfetch-org/test-repo
        patch: ext-test-repo-tag.patch

      - name: cpputest
        repo-path: cpputest/cpputest

To test the patch, update the project again but with the ``-f`` option to force
overwriting the local changes. The local changes will be lost but the patch will
be applied.

.. code-block:: console

  dfetch update -f ext/test-repo-tag

Now all changes can be amended to the last committed version including the patch.

.. code-block:: console

   git add ext/test-repo-tag ext-test-repo-tag.patch
   git commit --amend -no-edit

For more details on working with patches see :ref:`Diff` and :ref:`Patch`.

.. scenario-include:: ../features/journey-basic-patching.feature
