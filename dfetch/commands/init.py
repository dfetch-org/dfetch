"""*Dfetch* can generate a starting manifest.

It will be created in the current folder.
"""

import argparse
import os
import shutil

import dfetch.commands.command
from dfetch import DEFAULT_MANIFEST_NAME
from dfetch.log import get_logger
from dfetch.resources import TEMPLATE_PATH

logger = get_logger(__name__)


class Init(dfetch.commands.command.Command):
    """Initialize a manifest.

    Generate a manifest that can be used as basis for a project.
    """

    @staticmethod
    def create_menu(subparsers: "argparse._SubParsersAction") -> None:
        """Add the parser menu for this action."""
        dfetch.commands.command.Command.parser(subparsers, Init)

    def __call__(self, args: argparse.Namespace) -> None:
        """Perform the init."""
        del args  # unused

        if os.path.isfile(DEFAULT_MANIFEST_NAME):
            logger.warning(f"{DEFAULT_MANIFEST_NAME} already exists!")
            return

        with TEMPLATE_PATH as template_path:
            dest = shutil.copyfile(template_path, DEFAULT_MANIFEST_NAME)

        logger.info(f"Created {dest}")
