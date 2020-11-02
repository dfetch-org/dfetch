.. Dfetch documentation master file

Technical reference
===================

.. note :: This is a technical reference for other contributors, not needed for users.

There are three main packages in *Dfetch*:

- :ref:`Commands <dfetch.commands>` : modules related to handling the commandline
- :ref:`Project <dfetch.project>` : modules related to performing actions
- :ref:`Manifest <dfetch.manifest>` : modules related to parsing and interacting with the :ref:`Manifest`.

Each command that is available to the user inherits from the :ref:`Command base class`

dfetch.commands
---------------
.. automodule:: dfetch.commands
    :members:

Command base class
##################

.. autoclass:: dfetch.commands.command.Command
    :members:

Init class
##########

.. autoclass:: dfetch.commands.init.Init
    :members:

Check class
###########

.. autoclass:: dfetch.commands.check.Check
    :members:

Update class
############

.. autoclass:: dfetch.commands.update.Update
    :members:

Validate class
##############

.. autoclass:: dfetch.commands.validate.Validate
    :members:

dfetch.project
---------------
.. automodule:: dfetch.project
    :members:

VCS base class
##############

.. autoclass:: dfetch.project.vcs.VCS
    :members:
    :private-members:

GitRepo class
#############

.. autoclass:: dfetch.project.git.GitRepo
    :members:
    :private-members:

SvnRepo class
#############

.. autoclass:: dfetch.project.svn.SvnRepo
    :members:
    :private-members:

dfetch.manifest
---------------
.. automodule:: dfetch.manifest
    :members:

Manifest class
##############
.. autoclass:: dfetch.manifest.manifest.Manifest
    :members:
