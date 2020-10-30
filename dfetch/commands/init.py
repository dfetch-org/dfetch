"""
Note that you can validate your manifest using :ref:`validate`.

This will parse your :ref:`Manifest` and check if all fields can be parsed.
"""

import argparse
import logging
import os
import shutil

import dfetch.commands.command
from dfetch.util.util import find_file

SCRIPT_PATH = os.path.dirname(__file__)
logger = logging.getLogger(__name__)


class Init(dfetch.commands.command.Command):
    """Initialize a manifest.

    Generate a manifest that can be used as basis for a project.
    """

    TEMPLATE_PATH = find_file("template.yaml", SCRIPT_PATH)[0]
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

        dest = shutil.copyfile(self.TEMPLATE_PATH, self.MANIFEST_NAME)

        logger.info(f"Created {dest}")
