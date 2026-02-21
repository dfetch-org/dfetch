"""Formatting patches.

*Dfetch* allows you to keep local changes to external projects in the form of
patch files. These patch files should be created with the `dfetch diff` command.
However, these patch files are relative to the :ref:`source directory <Source>`
of the project inside the superproject. This makes it hard to apply these patches
upstream, as upstream projects usually expect patches to be relative to their
root directory. The ``format-patch`` command reformats all patches of a project
to make them usable for the upstream project.

.. code-block:: sh

   dfetch format-patch some-project

.. tabs::

    .. tab:: Git

        .. scenario-include:: ../features/format-patch-in-git.feature

    .. tab:: SVN

        .. scenario-include:: ../features/format-patch-in-svn.feature

"""

import argparse
import os
import pathlib
import re

import dfetch.commands.command
import dfetch.manifest.project
import dfetch.project
from dfetch.log import get_logger
from dfetch.project import create_super_project
from dfetch.project.gitsubproject import GitSubProject
from dfetch.project.subproject import SubProject
from dfetch.project.svnsubproject import SvnSubProject
from dfetch.util.util import catch_runtime_exceptions, in_directory
from dfetch.vcs.patch import Patch, PatchAuthor, PatchInfo, PatchType

logger = get_logger(__name__)


class FormatPatch(dfetch.commands.command.Command):
    """Format a patch to upstream any changes.

    The ``format-patch`` command reformats all patches of
    the given subprojects to make the patches usable for the
    upstream project. The patches are converted to the upstream
    vcs system if required and they are made absolute again.
    """

    @staticmethod
    def create_menu(subparsers: dfetch.commands.command.SubparserActionType) -> None:
        """Add the menu for the format-patch action."""
        parser = dfetch.commands.command.Command.parser(subparsers, FormatPatch)
        parser.add_argument(
            "projects",
            metavar="<project>",
            type=str,
            nargs="*",
            help="Specific project(s) to format patches of",
        )
        parser.add_argument(
            "-o",
            "--output-directory",
            metavar="<output_directory>",
            type=str,
            default=".",
            help="Output directory for formatted patches",
        )

    def __call__(self, args: argparse.Namespace) -> None:
        """Perform the format patch."""
        superproject = create_super_project()

        exceptions: list[str] = []

        output_dir_path = pathlib.Path(args.output_directory).resolve()

        if not output_dir_path.is_relative_to(superproject.root_directory):
            raise RuntimeError(
                f"Output directory '{output_dir_path}' must be inside"
                f" the superproject root '{superproject.root_directory}'"
            )

        output_dir_path.mkdir(parents=True, exist_ok=True)

        with in_directory(superproject.root_directory):
            for project in superproject.manifest.selected_projects(args.projects):
                with catch_runtime_exceptions(exceptions) as exceptions:
                    subproject = dfetch.project.create_sub_project(project)

                    # Check if the project has a patch, maybe suggest creating one?
                    if not subproject.patch:
                        logger.print_warning_line(
                            project.name,
                            f'skipped - there is no patch file, use "dfetch diff {project.name}"'
                            " to generate one instead",
                        )
                        continue

                    version = subproject.on_disk_version()
                    for idx, patch_file in enumerate(subproject.patch, start=1):

                        patch_info = PatchInfo(
                            author=PatchAuthor(
                                name=superproject.get_username(),
                                email=superproject.get_useremail(),
                            ),
                            subject=f"Patch for {project.name}",
                            total_patches=len(subproject.patch),
                            current_patch_idx=idx,
                            revision="" if not version else version.revision,
                        )

                        patch = Patch.from_file(patch_file).convert_type(
                            _determine_target_patch_type(subproject)
                        )
                        patch.add_prefix(
                            re.split(r"\*", subproject.source, 1)[0].rstrip("/")
                        )

                        output_patch_file = (
                            output_dir_path / pathlib.Path(patch_file).name
                        )
                        output_patch_file.write_text(
                            patch.dump_header(patch_info) + patch.dump(),
                            encoding="utf-8",
                        )

                        logger.print_info_line(
                            project.name,
                            f"formatted patch written to {output_patch_file.relative_to(os.getcwd())}",
                        )

        if exceptions:
            raise RuntimeError("\n".join(exceptions))


def _determine_target_patch_type(subproject: SubProject) -> PatchType:
    """Determine the subproject type for the patch."""
    if isinstance(subproject, GitSubProject):
        required_type = PatchType.GIT
    elif isinstance(subproject, SvnSubProject):
        required_type = PatchType.SVN
    else:
        required_type = PatchType.PLAIN

    return required_type
