"""Logging related items."""

import logging

import coloredlogs


def setup_root(name: str) -> logging.Logger:
    """Create the root logger."""
    logger = logging.getLogger(name)

    msg_format = "%(message)s"

    level_styles = {
        "critical": {"bold": True, "color": "magenta"},
        "debug": {"color": "green"},
        "error": {"color": "red"},
        "info": {"color": 4},
        "notice": {"color": "magenta"},
        "spam": {"color": "green", "faint": True},
        "success": {"bold": True, "color": "green"},
        "verbose": {"color": "blue"},
        "warning": {"color": "yellow"},
    }

    coloredlogs.install(fmt=msg_format, level_styles=level_styles, level="INFO")

    return logger


def increase_verbosity() -> None:
    """Increase the verbosity of the logger."""
    coloredlogs.increase_verbosity()
