"""*Dfetch* can create a patch file with your local changes to the external project.

Dfetch will use your project's version control system to find the change to the project
or a specific project since between two commits.

If no commits are provided *Dfetch* will create a patch between the commit the metadata file
was commited and the last version.

Using the generated patch
=========================
The patch can be used in the manifest see the patch attribute for more information.
It can also be sent to the upstream maintainer in case of bug fixes.

The maintainer can apply this patch as following:

Git
~~~

.. code-block:: console

   $ git apply --verbose --directory='target_dir' myfixes.patch
   Checking patch target_dir/some_file.cpp...
   Applied patch target_dir/some_file.cpp cleanly.

Svn
~~~

.. warning:: not supported yet

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
    """Diff a project.

    Create a patch of a project
    """

    @staticmethod
    def create_menu(subparsers: "argparse._SubParsersAction") -> None:
        """Add the parser menu for this action."""
        parser = dfetch.commands.command.Command.parser(subparsers, Diff)
        parser.add_argument(
            "--non-recursive",
            "-N",
            action="store_true",
            help="Don't recursively diff for child manifests.",
        )
        parser.add_argument(
            "-r",
            "--revs",
            metavar="<oldrev>[:<newrev>]",
            type=str,
            default="",
            help="Revision range",
        )

        parser.add_argument(
            "projects",
            metavar="<project>",
            type=str,
            nargs=1,
            help="Project to generate diff of",
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

    def generate_patch(self, path, revs, project, patch_name):
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
                f"the last commit to {Metadata.FILENAME} in {project.destination}",
                "Please either commit this, or specify a revision to start from with --revs",
            )

    if len(revs) == 1:
        revs.append(repo.current_revision())

    return repo.get_diff(*revs)
