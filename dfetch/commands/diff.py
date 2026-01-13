"""*Dfetch* can create a patch file with your local changes to the external project.

If you've found any issues with the remote project, you can fix them within the context of your project.
To help the upstream project, you can generate a patch file that can be applied by the upstream maintainer.
The patch will be generated using the version control system
of your main project (also referred to as superproject) that contains the manifest.

To generate a patch, *Dfetch* requires two revisions to identify the changes. You can
provide these through the ``--revs`` argument.

* If ``--revs`` is not provided the changes are calculated between the last revision
  the metadata file was changed and the working copy (also uncommitted changes).
* If ``--revs`` specifies one revision (e.g. ``--revs 23864ef2``), that revision will be used as starting point.
* Alternately both revisions can be explicitly specified, e.g. ``--revs 23864ef2:4a9cb18``.

The below statement will generate a patch for ``some-project`` from your manifest.

.. code-block:: sh

   dfetch diff some-project

.. tabs::

   .. tab:: Git

      .. scenario-include:: ../features/diff-in-git.feature

   .. tab:: SVN

      .. scenario-include:: ../features/diff-in-svn.feature

Using the generated patch
=========================
The patch can be used in the manifest; see the :ref:`patch` attribute for more information.
It can also be sent to the upstream maintainer in case of bug fixes.

The generated patch is a relative patch and should be by applied specifying the base directory of the *git repo*.
See below for the version control specifics. The patch will also contain the content of binary files.

.. tabs::

    .. tab:: Git

        .. code-block:: sh

            git apply --verbose --directory='some-project' some-project.patch

    .. tab:: SVN

        .. code-block:: sh

            svn patch some-project.patch

.. warning::

   The path given to ``--directory`` when applying the patch in a git repo, *must* be relative to the base
   directory of the repo, i.e. the folder where the ``.git`` folder is located.

   For example if you have the patch ``Core/MyModule/MySubmodule.patch``
   for files in the directory ``Core/MyModule/MySubmodule/`` and your current working directory is ``Core/MyModule/``.
   The correct command would be:

   ``git apply --verbose --directory='Core/MyModule/MySubmodule' MySubmodule.patch``

"""

import argparse
import os
import pathlib

import dfetch.commands.command
from dfetch.log import get_logger
from dfetch.project.superproject import SuperProject
from dfetch.util.util import catch_runtime_exceptions, in_directory

logger = get_logger(__name__)


class Diff(dfetch.commands.command.Command):
    """Generate a diff of a project.

    Create a patch of a project. The diff will be a relative patch file of
    only the project's directory.
    """

    @staticmethod
    def create_menu(subparsers: dfetch.commands.command.SubparserActionType) -> None:
        """Add the parser menu for this action."""
        parser = dfetch.commands.command.Command.parser(subparsers, Diff)
        parser.add_argument(
            "-r",
            "--revs",
            metavar="<oldrev>[:<newrev>]",
            type=str,
            default="",
            help="Revision(s) to generate diff from",
        )

        parser.add_argument(
            "projects",
            metavar="<project>",
            type=str,
            nargs=1,
            help="Project to generate diff from",
        )

    def __call__(self, args: argparse.Namespace) -> None:
        """Perform the diff."""
        superproject = SuperProject()
        old_rev, new_rev = self._parse_revs(args.revs)

        with in_directory(superproject.root_directory):
            exceptions: list[str] = []
            projects = superproject.manifest.selected_projects(args.projects)
            if not projects:
                raise RuntimeError(
                    f"No (such) project found! {', '.join(args.projects)}"
                )
            for project in projects:
                with catch_runtime_exceptions(exceptions) as exceptions:
                    if not os.path.exists(project.destination):
                        raise RuntimeError(
                            "You cannot generate a diff of a project that was never fetched"
                        )
                    subproject = superproject.get_sub_project(project)

                    if subproject is None:
                        raise RuntimeError(
                            "Can only create patch if your project is an SVN or Git repo",
                        )
                    old_rev = old_rev or subproject.metadata_revision()
                    patch = subproject.diff(old_rev, new_rev)

                    msg = self._rev_msg(old_rev, new_rev)
                    if patch:
                        patch_path = pathlib.Path(f"{project.name}.patch")
                        logger.print_info_line(
                            project.name,
                            f"Generating patch {patch_path} {msg} in {superproject.root_directory}",
                        )
                        patch_path.write_text(patch, encoding="UTF-8")
                    else:
                        logger.print_info_line(project.name, f"No diffs found {msg}")

        if exceptions:
            raise RuntimeError("\n".join(exceptions))

    @staticmethod
    def _parse_revs(revs_arg: str) -> tuple[str, str]:
        revs = [r for r in revs_arg.strip(":").split(":", maxsplit=1) if r]

        if len(revs) == 0:
            return "", ""
        if len(revs) == 1:
            return revs[0], ""
        return revs[0], revs[1]

    @staticmethod
    def _rev_msg(old_rev: str, new_rev: str) -> str:
        return f"from {old_rev} to {new_rev}" if new_rev else f"since {old_rev}"
