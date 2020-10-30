"""Updating is very important."""

import argparse
import logging
import os
from typing import List

import dfetch.commands.command
import dfetch.manifest.manifest
import dfetch.manifest.project
import dfetch.manifest.validate
import dfetch.project.git
import dfetch.project.svn

logger = logging.getLogger(__name__)


class Update(dfetch.commands.command.Command):
    """Update all modules from the manifest.

    Verifies the manifest and checks all dependencies if updates are available.
    """

    @staticmethod
    def create_menu(subparsers: "argparse._SubParsersAction") -> None:
        """Add the menu for the update action."""
        parser = dfetch.commands.command.Command.parser(subparsers, Update)
        parser.add_argument("--dry-run", "-n", action="store_true", help="Only check")

    def __call__(self, args: argparse.Namespace) -> None:
        """Perform the update."""
        logger.debug("Looking for manifest")
        manifest_path = dfetch.manifest.manifest.find_manifest()
        dfetch.manifest.validate.validate(manifest_path)

        logger.debug(f"Using manifest {manifest_path}")
        toplevel_dir = os.path.dirname(manifest_path)

        logger.debug(f"Switching to {toplevel_dir}")
        os.chdir(toplevel_dir)

        manifest = dfetch.manifest.manifest.Manifest.from_file(manifest_path)

        self._send_minions(manifest.projects)

    @staticmethod
    def _send_minions(projects: List[dfetch.manifest.project.ProjectEntry]) -> None:

        exceptions = []

        for project in projects:
            try:
                dfetch.project.make(project, logger.getChild(project.name)).update()
            except RuntimeError as exc:
                exceptions += [str(exc)]

        if exceptions:
            raise RuntimeError("\n".join(exceptions))
