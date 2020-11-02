"""*Dfetch* can generate a starting manifest.

It will be created in the current folder.
"""

import argparse
import logging
import os
import shutil

import dfetch.commands.command
from dfetch.resources import TEMPLATE_PATH

logger = logging.getLogger(__name__)


class Init(dfetch.commands.command.Command):
    """Initialize a manifest.

    Generate a manifest that can be used as basis for a project.
    """

    MANIFEST_NAME = "manifest.yaml"

    @staticmethod
    def create_menu(subparsers: "argparse._SubParsersAction") -> None:
        """Add the parser menu for this action."""
        dfetch.commands.command.Command.parser(subparsers, Init)

    def __call__(self, args: argparse.Namespace) -> None:
        """Perform the init."""
        del args  # unused

        if os.path.isfile(self.MANIFEST_NAME):
            logger.warning(f"{self.MANIFEST_NAME} already exists!")
            return

        with TEMPLATE_PATH as template_path:
            dest = shutil.copyfile(template_path, self.MANIFEST_NAME)

        logger.info(f"Created {dest}")
