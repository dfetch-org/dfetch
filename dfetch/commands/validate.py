"""*Dfetch* can validate a manifest without fetching anything.

``dfetch validate`` parses ``dfetch.yaml`` and checks every field against the
manifest schema — project names, URLs, version strings, source paths, and
integrity hashes are all verified. Any structural or type error is reported
immediately with a clear message pointing at the offending field.

This is useful in CI to catch manifest mistakes before a full ``dfetch update``
run, or as a quick sanity-check after hand-editing the file.

.. note::

   Validation also runs automatically at the start of every ``dfetch update``
   and ``dfetch check`` — a separate ``dfetch validate`` step is only needed
   when you want to check the manifest without triggering a fetch.

.. scenario-include:: ../features/validate-manifest.feature

"""

import argparse
import os

import dfetch.commands.command
from dfetch.log import get_logger
from dfetch.manifest.parse import find_manifest, parse

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
        parse(manifest_path)
        manifest_path = os.path.relpath(manifest_path, os.getcwd())
        logger.print_report_line(manifest_path, "valid")
