"""List metadata of all projects listed in the manifest.

For each project listed in the manifest the metadata is shown,
such as timestamp of last fetch, revision, remote url, etc.
"""

import argparse
import os

import dfetch.commands.command
import dfetch.manifest.manifest
from dfetch.log import get_logger
from dfetch.project.metadata import Metadata

logger = get_logger(__name__)


class List(dfetch.commands.command.Command):
    """List metadata for each project.

    List all information provided in manifest and metadata files.
    """

    @staticmethod
    def create_menu(subparsers: "argparse._SubParsersAction") -> None:
        """Add the parser menu for this action."""
        dfetch.commands.command.Command.parser(subparsers, List)

    def __call__(self, args: argparse.Namespace) -> None:
        """Perform the list."""
        manifest, path = dfetch.manifest.manifest.get_manifest()

        with dfetch.util.util.in_directory(os.path.dirname(path)):
            for project in manifest.projects:
                metadata = Metadata.from_file(Metadata.from_project_entry(project).path)
                logger.print_info_line("project", project.name)
                logger.print_info_line("    remote", project.remote)
                logger.print_info_line("    remote url", metadata.remote_url)
                logger.print_info_line("    branch", metadata.branch)
                logger.print_info_line("    last fetch", metadata.last_fetch)
                logger.print_info_line("    revision", metadata.revision)
