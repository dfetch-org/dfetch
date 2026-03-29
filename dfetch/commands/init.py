"""*Dfetch* can generate a starting manifest.

Running ``dfetch init`` creates a ``dfetch.yaml`` file in the current
directory. The file contains a minimal template that you can open and edit
directly, or populate incrementally using :ref:`dfetch add <add>`.

Once you have listed your dependencies, fetch them with :ref:`dfetch update <update>`.

If a ``dfetch.yaml`` already exists in the current directory, *Dfetch*
prints a warning and exits without overwriting it.
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
    def create_menu(subparsers: dfetch.commands.command.SubparserActionType) -> None:
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
