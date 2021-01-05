.. Dfetch documentation master file

Getting Started
===============

Main Concepts
-------------
Your project depends on other projects to build or run. In order keep the dependencies
with your project. *Dfetch* can fetch these dependencies and place them with your code.

*Dfetch* starts from a :ref:`Manifest` file. This contains all the :ref:`Projects`
this project is depending on. You as a user can then let *Dfetch* :ref:`update`
your dependencies.

*Dfetch* will fetch the correct version of your dependencies and place them in the
location of your choice. If the folder already exists and the version was updated
*Dfetch* will overwrite the folder with the changes.

You can then review the changes in your favorite version control system and commit
the changes as you please.

My first manifest
-----------------
For a complete description of the manifest, see :ref:`Manifest`.

*Dfetch* can generate a basic manifest as starting point with :ref:`dfetch init <init>`.

Below manifest will retrieve the given revision of *mymodule* from the remote listed.

.. code-block:: yaml

    manifest:
        version: 0.0

        remotes:
        - name: mycompany-git-modules
          url-base: http://git.mycompany.local/mycompany/

        projects:
         - name: mymodule
           repo-path: mymodule.git
           dst: external/mycompany/
           revision: eff03340c

My first update
---------------
After creating the manifest we can let *Dfetch* perform an update.
Make sure that you have installed *Dfetch* as described in :ref:`Installation`.

From a command-line perform the following command:

.. code-block::

   dfetch update

*Dfetch* will search through all directories down untill it finds the ``dfetch.yaml``
manifest and it will perform the update.

After *Dfetch* finishes, the version of the dependency as listed in your manifest is
downloaded at the target location. You can now commit it to your version control system.

My first version change
-----------------------
During development of your project you can periodically check for update with.

.. code-block::

   dfetch check

*Dfetch* will check for each project if a newer version is avaiable.
If you want to update and have an explicit revision in your :ref:`Manifest`:,
you can manually update the revision of the project.

.. note:: If you only have a branch specified, *Dfetch* will update automatically.

.. code-block:: yaml

    manifest:
        version: 0.0

        remotes:
        - name: mycompany-git-modules
          url-base: http://git.mycompany.local/mycompany/

        projects:
         - name: mymodule
           repo-path: mymodule.git
           dst: external/mycompany/
           revision: dgh45vb435

And after that rerunning `update`:

.. code-block::

   dfetch update

Now you can review the changes and commit them once again if you are happy.
