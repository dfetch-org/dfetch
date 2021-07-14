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

    @staticmethod
    def none_if_empty(field: str) -> str:
        """Return none string when empty, otherwise returns original."""
        return field if field else "<none>"

    def __call__(self, args: argparse.Namespace) -> None:
        """Perform the list."""
        manifest, path = dfetch.manifest.manifest.get_manifest()

        with dfetch.util.util.in_directory(os.path.dirname(path)):
            for project in manifest.projects:
                logger.print_info_line("project", project.name)
                logger.print_info_line("    remote", List.none_if_empty(project.remote))
                try:
                    metadata = Metadata.from_file(
                        Metadata.from_project_entry(project).path
                    )
                    logger.print_info_line(
                        "    remote url", List.none_if_empty(metadata.remote_url)
                    )
                    logger.print_info_line(
                        "    branch", List.none_if_empty(metadata.branch)
                    )
                    logger.print_info_line("    tag", List.none_if_empty(metadata.tag))
                    logger.print_info_line(
                        "    last fetch", List.none_if_empty(metadata.last_fetch)
                    )
                    logger.print_info_line(
                        "    revision", List.none_if_empty(metadata.revision)
                    )
                except FileNotFoundError:
                    logger.print_info_line("    last fetch", "never")
