"""Logging related items."""

import logging
import os
import sys
from typing import Any, Optional, cast

from rich.console import Console
from rich.highlighter import NullHighlighter
from rich.logging import RichHandler

from dfetch import __version__


def make_console(no_color: bool = False) -> Console:
    """Create a Rich Console with proper color handling."""
    return Console(
        no_color=no_color
        or os.getenv("NO_COLOR") is not None
        or not sys.stdout.isatty()
    )


def configure_root_logger(console: Optional[Console] = None) -> None:
    """Configure the root logger with RichHandler using the provided Console."""
    console = console or make_console()

    handler = RichHandler(
        console=console,
        show_time=False,
        show_path=False,
        show_level=False,
        markup=True,
        rich_tracebacks=True,
        highlighter=NullHighlighter(),
    )

    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[handler],
        force=True,
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


def setup_root(name: str, console: Optional[Console] = None) -> DLogger:
    """Create and return the root logger."""
    logging.setLoggerClass(DLogger)
    configure_root_logger(console)
    logger = logging.getLogger(name)
    return cast(DLogger, logger)


def increase_verbosity() -> None:
    """Increase verbosity of the root logger."""
    levels = [
        logging.CRITICAL,
        logging.ERROR,
        logging.WARNING,
        logging.INFO,
        logging.DEBUG,
    ]
    logger_ = logging.getLogger()
    current_level = logger_.getEffectiveLevel()
    try:
        idx = levels.index(current_level)
        if idx < len(levels) - 1:
            new_level = levels[idx + 1]
        else:
            new_level = levels[-1]
    except ValueError:
        new_level = logging.DEBUG
    logger_.setLevel(new_level)


def get_logger(name: str, console: Optional[Console] = None) -> DLogger:
    """Get logger for a module, optionally configuring console colors."""
    logging.setLoggerClass(DLogger)
    logger = logging.getLogger(name)
    logger.propagate = True
    if console:
        configure_root_logger(console)
    return cast(DLogger, logger)


def configure_external_logger(name: str, level: int = logging.INFO) -> None:
    """Configure an external logger from a third party package."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = True
    logger.handlers.clear()
