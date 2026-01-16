"""Logging related items."""

import logging
from typing import Any, Optional, cast

from rich.highlighter import NullHighlighter
from rich.logging import RichHandler

from dfetch import __version__

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[
        RichHandler(
            show_time=False,
            show_path=False,
            show_level=False,
            markup=True,
            rich_tracebacks=True,
            highlighter=NullHighlighter(),
        )
    ],
)


class DLogger(logging.Logger):
    """Logging class extended with specific log items for dfetch."""

    def print_info_line(self, name: str, info: str) -> None:
        """Print a line of info."""
        self.info(
            f"  [bold][bright_green]{name:20s}:[/bright_green][blue] {info}[/blue][/bold]"
        )

    def print_warning_line(self, name: str, info: str) -> None:
        """Print a warning line: green name, yellow value."""
        self.warning(
            f"  [bold][bright_green]{name:20s}:[/bright_green][bright_yellow] {info}[/bright_yellow][/bold]"
        )

    def print_title(self) -> None:
        """Print the DFetch tool title and version."""
        self.info(f"[bold blue]Dfetch ({__version__})[/bold blue]")

    def print_info_field(self, field_name: str, field: str) -> None:
        """Print a field with corresponding value."""
        self.print_info_line(field_name, field if field else "<none>")

    def warning(self, msg: object, *args: Any, **kwargs: Any) -> None:
        """Log warning."""
        super().warning(
            f"[bold bright_yellow]{msg}[/bold bright_yellow]", *args, **kwargs
        )

    def error(self, msg: object, *args: Any, **kwargs: Any) -> None:
        """Log error."""
        super().error(f"[red]{msg}[/red]", *args, **kwargs)


def setup_root(name: str) -> DLogger:
    """Create the root logger."""
    logging.setLoggerClass(DLogger)
    logger = logging.getLogger(name)
    return cast(DLogger, logger)


def increase_verbosity(logger: Optional[DLogger] = None) -> None:
    """Increase the verbosity of a logger."""
    levels = [
        logging.CRITICAL,
        logging.ERROR,
        logging.WARNING,
        logging.INFO,
        logging.DEBUG,
    ]
    logger_ = logger or logging.getLogger("dfetch")
    current_level = logger_.getEffectiveLevel()  # <- check effective level
    try:
        idx = levels.index(current_level)
        # step to next more verbose level (lower number)
        new_level = levels[min(idx + 1, len(levels) - 1)]
    except ValueError:
        new_level = logging.DEBUG
    logger_.setLevel(new_level)


def get_logger(name: str) -> DLogger:
    """Get logger for a module."""
    logging.setLoggerClass(DLogger)
    logger = logging.getLogger(name)
    logger.propagate = True
    return cast(DLogger, logger)


def configure_external_logger(name: str, level: int = logging.INFO) -> None:
    """Configure an external logger from a third party package."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = True
