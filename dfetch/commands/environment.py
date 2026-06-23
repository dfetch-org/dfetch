"""*Dfetch* can report information about its working environment.

``dfetch environment`` prints:

* **Platform** — operating system name and kernel version.
* **VCS tool versions** — the version of each supported VCS client
  (Git, SVN) found on ``PATH``.

Run this command when setting up a new machine to confirm that the required
VCS tools are installed and discoverable, or include the output when filing
a bug report so that developers can reproduce your environment exactly.
"""

import argparse
import platform

import dfetch.commands.command
from dfetch import __version__
from dfetch.log import get_logger
from dfetch.project import SUPPORTED_SUBPROJECT_TYPES
from dfetch.util.github_version_check import newer_version_available

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
        logger.debug("Checking for a newer dfetch version")
        newer = newer_version_available()
        if newer:
            dfetch_info = (
                f"{__version__} ({newer} available"
                " see https://github.com/dfetch-org/dfetch/releases)"
            )
        else:
            dfetch_info = __version__
        logger.print_report_line("dfetch", dfetch_info)
        logger.print_report_line(
            "platform", f"{platform.system()} {platform.release()}"
        )
        for project_type in SUPPORTED_SUBPROJECT_TYPES:
            project_type.list_tool_info()
