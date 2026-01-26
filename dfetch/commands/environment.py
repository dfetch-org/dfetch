"""*Dfetch* can generate output about its working environment."""

import argparse
import platform

import dfetch.commands.command
from dfetch.log import get_logger
from dfetch.project import SUPPORTED_PROJECT_TYPES

logger = get_logger(__name__)


class Environment(dfetch.commands.command.Command):
    """Get information about the environment dfetch is working in.

    Generate output that can be used by dfetch developers to investigate issues.
    """

    @staticmethod
    def create_menu(subparsers: dfetch.commands.command.SubparserActionType) -> None:
        """Add the parser menu for this action."""
        dfetch.commands.command.Command.parser(subparsers, Environment)

    def __call__(self, _: argparse.Namespace) -> None:
        """Perform listing the environment."""
        logger.print_report_line(
            "platform", f"{platform.system()} {platform.release()}"
        )
        for project_type in SUPPORTED_PROJECT_TYPES:
            project_type.list_tool_info()
