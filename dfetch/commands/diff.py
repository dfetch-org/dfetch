"""*Dfetch* can create a patch file with your local changes to the external project.

If you've found any issues with the remote project, you can fix them within the context of your project.
To help the upstream project, you can generate a patch file
that can be applied by the upstream maintainer. The patch will be generated using the version control system
of your main project that contains the manifest.

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

Updating the patch
======================
If you have further changes to a project with a patch, you can update the patch by first reversing the patch, using
``apply`` and with the ``--directory`` argument as shown above. To reverse the patch you also require the ``-R``.
This will return the project to the state before the patch was applied. You can then stage the project and re-apply
the patch to the project to have an editable patch.

.. code-block:: sh

   # First apply the reverse patch
   git apply --verbose --directory='some-project' -R some-project.patch

   # Stage the project in its unpatched state
   git add some-project

   # Re-apply the patch
   git apply --verbose --directory='some-project' some-project.patch

Now you can make further changes to the project, and re-generate the patch using the raw git command as shown below.

.. code-block:: sh

   # Generate the patch from the directory again
   cd some-project
   git diff --relative --binary --no-ext-diff --no-color . > ../some-project.patch

   # Force a fetch and update the patch to test your changes
   dfetch update -f some-project

"""

import argparse
import os

import dfetch.commands.command
import dfetch.manifest.manifest
import dfetch.manifest.validate
import dfetch.project
from dfetch.log import get_logger
from dfetch.manifest.project import ProjectEntry
from dfetch.project.git import GitRepo
from dfetch.project.metadata import Metadata
from dfetch.project.svn import SvnRepo
from dfetch.project.vcs import VCS
from dfetch.util.util import catch_runtime_exceptions, in_directory
from dfetch.vcs.git import GitLocalRepo

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
        manifest = dfetch.manifest.manifest.get_manifest()
        revs = [r for r in args.revs.strip(":").split(":", maxsplit=1) if r]

        with in_directory(os.path.dirname(manifest.path)):
            exceptions: list[str] = []
            projects = manifest.selected_projects(args.projects)
            if not projects:
                raise RuntimeError(
                    f"No (such) project found! {', '.join(args.projects)}"
                )
            for project in projects:
                patch_name = f"{project.name}.patch"
                with catch_runtime_exceptions(exceptions) as exceptions:
                    repo = _get_repo(manifest.path, project)
                    patch = _diff_from_repo(repo, project, revs)

                    _dump_patch(manifest.path, revs, project, patch_name, patch)

        if exceptions:
            raise RuntimeError("\n".join(exceptions))


def _get_repo(path: str, project: ProjectEntry) -> VCS:
    """Get the repo type from the project."""
    if not os.path.exists(project.destination):
        raise RuntimeError(
            "You cannot generate a diff of a project that was never fetched"
        )
    main_project_dir = os.path.dirname(path)
    if GitLocalRepo(main_project_dir).is_git():
        return GitRepo(project)
    if SvnRepo.check_path(main_project_dir):
        return SvnRepo(project)

    raise RuntimeError(
        "Can only create patch in SVN or Git repo",
    )


def _diff_from_repo(repo: VCS, project: ProjectEntry, revs: list[str]) -> str:
    """Generate a relative diff for a svn repo."""
    if len(revs) > 2:
        raise RuntimeError(f"Too many revisions given! {revs}")

    if not revs:
        revs.append(repo.metadata_revision())
        if not revs[-1]:
            raise RuntimeError(
                "When not providing any commits, dfetch starts from"
                f" the last commit to {Metadata.FILENAME} in {project.destination}."
                " Please either commit this, or specify a revision to start from with --revs"
            )

    if len(revs) == 1:
        revs.append("")

    return repo.get_diff(
        old_revision=revs[0], new_revision=revs[1], ignore=(Metadata.FILENAME,)
    )


def _dump_patch(
    path: str, revs: list[str], project: ProjectEntry, patch_name: str, patch: str
) -> None:
    """Dump the patch to a file."""
    if patch:
        rev_range = f"from {revs[0]} to {revs[1]}" if revs[1] else f"since {revs[0]}"
        logger.print_info_line(
            project.name,
            f"Generating patch {patch_name} {rev_range} in {os.path.dirname(path)}",
        )
        with open(patch_name, "w", encoding="UTF-8") as patch_file:
            patch_file.write(patch)
    else:
        if revs[1]:
            msg = f"No diffs found from {revs[0]} to {revs[1]}"
        else:
            msg = f"No diffs found since {revs[0]}"

        logger.print_info_line(project.name, msg)
