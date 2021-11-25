"""*Dfetch* can create a patch file with your local changes to the external project.

If you've found any issues with the remote project, you can fix these issues inside the
context of your project. To help the upstream project, you can generate a patch file
that can be applied by the upstream maintainer. The patch will be generated with the
version control system of your main project that contains the manifest.

To generate a patch, *Dfetch* requires two revisions to determine the changes. You can
provide these through the ``--revs`` argument.

* If ``--revs`` is not provided the changes are calculated between the last revision
  the metadata file was changed and the current version.
* If ``--revs`` specifies one revision (e.g. ``--revs 23864ef2``), that revision will be used as starting point.
* Alternately both revisions can be explicitly specified, e.g. ``--revs 23864ef2:4a9cb18``.

The below statement will generate a patch for ``some-project`` from your manifest.

.. code-block:: console

   $ dfetch diff some-project


Using the generated patch
=========================
The patch can be used in the manifest see the :ref:`patch` attribute for more information.
It can also be sent to the upstream maintainer in case of bug fixes.

The patch generated is a relative patch and should be applied specifying the base directory.
See below for the version control specifics.

.. code-block:: sh

   # For git repo's
   git apply --verbose --directory='some-project' some-project.patch

   # For svn repo's
   svn patch some-project.patch

"""

import argparse
import os
from typing import List

import dfetch.commands.command
import dfetch.manifest.manifest
import dfetch.manifest.validate
import dfetch.project
from dfetch.log import get_logger
from dfetch.manifest.project import ProjectEntry
from dfetch.project.git import GitRepo
from dfetch.project.metadata import Metadata
from dfetch.project.svn import SvnRepo
from dfetch.util.util import catch_runtime_exceptions, in_directory
from dfetch.vcs.git import GitLocalRepo

logger = get_logger(__name__)


class Diff(dfetch.commands.command.Command):
    """Generate a diff of a project.

    Create a patch of a project. The diff will be a relative patch file
    only of the project's directory.
    """

    @staticmethod
    def create_menu(subparsers: "argparse._SubParsersAction") -> None:
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
        manifest, path = dfetch.manifest.manifest.get_manifest()
        revs = [r for r in args.revs.strip(":").split(":", maxsplit=1) if r]

        with in_directory(os.path.dirname(path)):
            exceptions: List[str] = []
            projects = manifest.selected_projects(args.projects)
            if not projects:
                raise RuntimeError(
                    f"No (such) project found! {', '.join(args.projects)}"
                )
            for project in projects:
                patch_name = f"{project.name}.patch"
                with catch_runtime_exceptions(exceptions) as exceptions:

                    self.generate_patch(path, revs, project, patch_name)

        if exceptions:
            raise RuntimeError("\n".join(exceptions))

    @staticmethod
    def generate_patch(
        path: str, revs: List[str], project: ProjectEntry, patch_name: str
    ) -> None:
        """Generate a patch for the given project."""
        if not os.path.exists(project.destination):
            raise RuntimeError(
                "You cannot generate a diff of a project that was never fetched"
            )
        if GitLocalRepo(project.destination).is_git():
            patch = _diff_from_git(project, revs)
        elif SvnRepo.check_path(project.destination):
            raise NotImplementedError("To be done!")
        else:
            raise RuntimeError(
                "Can only create patch in SVN or Git repo",
            )

        if patch:
            logger.print_info_line(
                project.name,
                f"Generating patch {patch_name} from {revs[0]} to {revs[1]} in {os.path.dirname(path)}",
            )
            with open(patch_name, "w", encoding="UTF-8") as patch_file:
                patch_file.write(patch)
        else:
            logger.print_info_line(
                project.name, f"No diffs found from {revs[0]} to {revs[1]}"
            )


def _diff_from_git(project: ProjectEntry, revs: List[str]) -> str:
    """Generate a relative diff for a git repo."""
    repo = GitRepo(project)

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
        revs.append(repo.current_revision())

    return repo.get_diff(*revs)
