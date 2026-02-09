"""Logging related items."""

import logging
import os
import sys
from contextlib import nullcontext
from typing import Any, cast

from rich.console import Console
from rich.highlighter import NullHighlighter
from rich.logging import RichHandler
from rich.status import Status

from dfetch import __version__


def make_console(no_color: bool = False) -> Console:
    """Create a Rich Console with proper color handling."""
    return Console(
        no_color=no_color
        or os.getenv("NO_COLOR") is not None
        or not sys.stdout.isatty()
    )


def configure_root_logger(console: Console | None = None) -> None:
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

    _printed_projects: set[str] = set()

    def print_report_line(self, name: str, info: str) -> None:
        """Print a line for a report."""
        self.info(
            f"  [bold][bright_green]{name:20s}:[/bright_green][blue] {info}[/blue][/bold]"
        )

    def print_info_line(self, name: str, info: str) -> None:
        """Print a line of info, only printing the project name once."""
        if name not in DLogger._printed_projects:
            self.info(f"  [bold][bright_green]{name}:[/bright_green][/bold]")
            DLogger._printed_projects.add(name)

        line = info.replace("\n", "\n    ")
        self.info(f"  [bold blue]> {line}[/bold blue]")

    def print_warning_line(self, name: str, info: str) -> None:
        """Print a warning line: green name, yellow value."""
        if name not in DLogger._printed_projects:
            self.info(f"  [bold][bright_green]{name}:[/bright_green][/bold]")
            DLogger._printed_projects.add(name)

        line = info.replace("\n", "\n    ")
        self.info(f"  [bold bright_yellow]> {line}[/bold bright_yellow]")

    def print_title(self) -> None:
        """Print the DFetch tool title and version."""
        self.info(f"[bold blue]Dfetch ({__version__})[/bold blue]")

    def print_info_field(self, field_name: str, field: str) -> None:
        """Print a field with corresponding value."""
        self.print_report_line(field_name, field if field else "<none>")

    def warning(self, msg: object, *args: Any, **kwargs: Any) -> None:
        """Log warning."""
        super().warning(
            f"[bold bright_yellow]{msg}[/bold bright_yellow]", *args, **kwargs
        )

    def error(self, msg: object, *args: Any, **kwargs: Any) -> None:
        """Log error."""
        super().error(f"[red]{msg}[/red]", *args, **kwargs)

    def status(
        self, name: str, message: str, spinner: str = "dots", enabled: bool = True
    ) -> Status | nullcontext[None]:
        """Show status message with spinner if enabled."""
        rich_console = None
        logger: logging.Logger | None = self
        while logger:
            for handler in getattr(logger, "handlers", []):
                if isinstance(handler, RichHandler):
                    rich_console = handler.console
                    break
            if rich_console or not getattr(logger, "parent", None):
                break
            logger = logger.parent

        if not rich_console or not enabled:
            return nullcontext(None)

        if name not in DLogger._printed_projects:
            self.info(f"  [bold][bright_green]{name}:[/bright_green][/bold]")
            DLogger._printed_projects.add(name)

        return Status(
            f"[bold bright_blue]> {message}[/bold bright_blue]",
            spinner=spinner,
            console=rich_console,
        )

    @classmethod
    def reset_projects(cls) -> None:
        """Clear the record of printed project names."""
        cls._printed_projects.clear()


class ExtLogFilter(logging.Filter):  # pylint: disable=too-few-public-methods
    """Adds indentation to all log messages that pass through this filter."""

    def __init__(self, prefix: str = "    "):
        """Initialize the ExtLogFilter with a prefix."""
        super().__init__()
        self.prefix = prefix

    def filter(self, record: logging.LogRecord) -> bool:
        """Add indentation to the log record message."""
        color = "blue" if record.levelno < logging.WARNING else "yellow"

        line = record.msg.replace("\n", "\n    ")
        record.msg = f"{self.prefix}[{color}]{line}[/{color}]"
        return True


def setup_root(name: str, console: Console | None = None) -> DLogger:
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


def get_logger(name: str, console: Console | None = None) -> DLogger:
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
    logger.addFilter(ExtLogFilter())
