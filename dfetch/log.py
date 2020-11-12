"""Logging related items."""

import logging

import coloredlogs


def setup_root(name: str) -> logging.Logger:
    """Create the root logger."""
    logger = logging.getLogger(name)

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
