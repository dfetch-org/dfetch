"""Note that you can validate your manifest using :ref:`validate`.

This will parse your :ref:`Manifest` and check if all fields can be parsed.

.. scenario-include:: ../features/validate-manifest.feature

"""

import argparse
import os

import dfetch.commands.command
from dfetch.log import get_logger
from dfetch.manifest.manifest import find_manifest
from dfetch.manifest.validate import validate

logger = get_logger(__name__)


class Validate(dfetch.commands.command.Command):
    """Validate a manifest.

    The Manifest is validated against a schema. See manifest for requirements.
    Note that each time either ``update`` or ``check`` is run, the manifest is also validated.
    """

    @staticmethod
    def create_menu(subparsers: dfetch.commands.command.SubparserActionType) -> None:
        """Add the parser menu for this action."""
        dfetch.commands.command.Command.parser(subparsers, Validate)

    def __call__(self, args: argparse.Namespace) -> None:
        """Perform the validation."""
        del args  # unused

        manifest_path = find_manifest()
        validate(manifest_path)
        manifest_path = os.path.relpath(manifest_path, os.getcwd())
        logger.print_info_line(manifest_path, "valid")
