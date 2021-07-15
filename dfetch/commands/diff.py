"""Create a patch of a project.

Find the changes commited since the last fetch and generate a patch file for that.
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
from dfetch.project.svn import SvnRepo
from dfetch.util.util import catch_runtime_exceptions, in_directory

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
            "projects",
            metavar="<project>",
            type=str,
            nargs=1,
            help="Project to generate diff of",
        )

    def __call__(self, args: argparse.Namespace) -> None:
        """Perform the diff."""
        manifest, path = dfetch.manifest.manifest.get_manifest()

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

                    if GitRepo.check_path(project.destination):
                        patch = _diff_from_git(project)
                    elif SvnRepo.check_path(project.destination):
                        raise NotImplementedError("To be done!")
                    else:
                        raise RuntimeError(
                            "Can only create patch in SVN or Git repo",
                        )

                    if patch:
                        logger.print_info_line(
                            project.name,
                            f"Generating patch {patch_name} in {os.path.dirname(path)}",
                        )
                        with open(patch_name, "w") as patch_file:
                            patch_file.write(patch)
                    else:
                        logger.print_info_line(project.name, "No diffs found!")

        if exceptions:
            raise RuntimeError("\n".join(exceptions))


def _diff_from_git(project: ProjectEntry) -> str:
    """Generate a relative diff for a git repo."""
    repo = GitRepo(project)
    hash_of_manifest = repo.metadata_revision()
    current_hash = repo.current_revision()

    return repo.get_diff(hash_of_manifest, current_hash)
