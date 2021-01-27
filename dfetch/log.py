"""Logging related items."""

import logging
from typing import cast

import coloredlogs
from colorama import Fore

from dfetch import __version__


class DLogger(logging.Logger):
    """Logging class extended with specific log items for dfetch."""

    def print_info_line(self, name: str, info: str) -> None:
        """Print a line of info."""
        self.info(f"  {Fore.GREEN}{name:20s}:{Fore.BLUE} {info}")

    def print_title(self) -> None:
        """Print the DFetch tool title and version."""
        self.info(f"{Fore.BLUE}Dfetch ({__version__})")


def setup_root(name: str) -> DLogger:
    """Create the root logger."""
    logger = get_logger(name)

    msg_format = "%(message)s"

    level_style = {
        "critical": {"color": "magenta", "bright": True, "bold": True},
        "debug": {"color": "green", "bright": True, "bold": True},
        "error": {"color": "red", "bright": True, "bold": True},
        "info": {"color": 4, "bright": True, "bold": True},
        "notice": {"color": "magenta", "bright": True, "bold": True},
        "spam": {"color": "green", "faint": True},
        "success": {"color": "green", "bright": True, "bold": True},
        "verbose": {"color": "blue", "bright": True, "bold": True},
        "warning": {"color": "yellow", "bright": True, "bold": True},
    }

    coloredlogs.install(fmt=msg_format, level_styles=level_style, level="INFO")

    return logger


def increase_verbosity() -> None:
    """Increase the verbosity of the logger."""
    coloredlogs.increase_verbosity()


def get_logger(name: str) -> DLogger:
    """Get logger for a module."""
    logging.setLoggerClass(DLogger)
    return cast(DLogger, logging.getLogger(name))
