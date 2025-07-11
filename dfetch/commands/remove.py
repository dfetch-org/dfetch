import argparse
import os
import shutil

import dfetch.commands.command
from dfetch import DEFAULT_MANIFEST_NAME
from dfetch.log import get_logger
from dfetch.manifest.manifest import get_manifest
from dfetch.util.util import in_directory, safe_rm

logger = get_logger(__name__)


class Remove(dfetch.commands.command.Command):
    """Remove a project from the manifest,

    Backup manifest, and remove project directory from disk.
    """

    @staticmethod
    def create_menu(subparsers: dfetch.commands.command.SubparserActionType) -> None:
        """Add the menu for the update action."""
        parser = dfetch.commands.command.Command.parser(subparsers, Remove)
        parser.add_argument(
            "projects",
            metavar="<project>",
            type=str,
            nargs="*",
            help="Specific project(s) to remove",
        )

    def __call__(self, args: argparse.Namespace) -> None:
        """Perform the remove action."""

        manifest, path = get_manifest()

        with in_directory(os.path.dirname(path)):
            for project in args.projects:

                manifest.remove(project)
                logger.info(f"Project '{project}' removed from manifest.")

                safe_rm(project)

            shutil.move(DEFAULT_MANIFEST_NAME, DEFAULT_MANIFEST_NAME + ".backup")
            manifest.dump(path)
