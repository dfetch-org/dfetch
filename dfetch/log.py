"""Logging related items."""

import logging
import os
import sys
import types
from contextlib import nullcontext
from typing import Any, cast

from rich._log_render import LogRender  # type: ignore[import-untyped]
from rich.console import Console
from rich.highlighter import NullHighlighter
from rich.logging import RichHandler
from rich.markup import escape as markup_escape
from rich.status import Status

from dfetch import __version__


def _make_non_expanding_log_render(**kwargs: Any) -> Any:
    """Return a LogRender callable that disables table expansion.

    Used when recording with asciinema to prevent Rich's ``expand=True`` from
    padding log lines to the full terminal width, which produces spurious blank
    lines in the cast player.
    """
    renderer = LogRender(**kwargs)

    def _render(*args: Any, **kw: Any) -> Any:
        table = renderer(*args, **kw)
        table.expand = False
        return table

    return _render


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

    if os.getenv("ASCIINEMA_REC"):
        # Rich's LogRender uses expand=True on its Table.grid, which pads every
        # log message with trailing spaces to fill the full terminal width.  When
        # asciinema records the output the padded line fills the terminal exactly,
        # causing the subsequent newline to produce a blank line in the cast
        # player.  Wrapping _log_render so it returns a non-expanding table
        # removes the trailing spaces and avoids the spurious blank lines.
        no_expand = _make_non_expanding_log_render(
            show_time=False, show_level=False, show_path=False
        )
        handler._log_render = no_expand  # pylint: disable=protected-access

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
        safe_name = markup_escape(name)
        safe_info = markup_escape(info)
        self.info(
            f"  [bold][bright_green]{safe_name:20s}:[/bright_green][blue] {safe_info}[/blue][/bold]"
        )

    def print_info_line(self, name: str, info: str) -> None:
        """Print a line of info, only printing the project name once."""
        if name not in DLogger._printed_projects:
            safe_name = markup_escape(name)
            self.info(f"  [bold][bright_green]{safe_name}:[/bright_green][/bold]")
            DLogger._printed_projects.add(name)

        if info:
            line = markup_escape(info).replace("\n", "\n    ")
            self.info(f"  [bold blue]> {line}[/bold blue]")

    def print_warning_line(self, name: str, info: str) -> None:
        """Print a warning line: green name, yellow value."""
        if name not in DLogger._printed_projects:
            safe_name = markup_escape(name)
            self.info(f"  [bold][bright_green]{safe_name}:[/bright_green][/bold]")
            DLogger._printed_projects.add(name)

        line = markup_escape(info).replace("\n", "\n    ")
        self.info(f"  [bold bright_yellow]> {line}[/bold bright_yellow]")

    def print_overview(self, name: str, title: str, info: dict[str, Any]) -> None:
        """Print an overview of fields."""
        self.print_info_line(name, title)
        for key, value in info.items():
            safe_key = markup_escape(str(key))
            if isinstance(value, list):
                self.info(f"      [blue]{safe_key + ':':20s}[/blue]")
                for item in value:
                    self.info(
                        f"      {'':20s}[white]- {markup_escape(str(item))}[/white]"
                    )
            else:
                self.info(
                    f"      [blue]{safe_key + ':':20s}[/blue][white] {markup_escape(str(value))}[/white]"
                )

    def print_title(self) -> None:
        """Print the DFetch tool title and version."""
        self.info(f"[bold blue]Dfetch ({__version__})[/bold blue]")

    def print_info_field(self, field_name: str, field: str) -> None:
        """Print a field with corresponding value."""
        self.print_report_line(field_name, field if field else "<none>")

    def print_yaml(self, fields: dict[str, Any]) -> None:
        """Print all str and list values in *fields* in YAML style."""
        first = True
        for key, value in fields.items():
            if isinstance(value, (str, list)):
                self.print_yaml_field(key, value, first=first)
                first = False

    def print_yaml_field(
        self, key: str, value: str | list[str], *, first: bool = False
    ) -> None:
        """Print one manifest field in YAML style.

        When *first* is True the line is prefixed with ``- `` (YAML sequence
        entry marker) and subsequent fields are indented with four spaces so
        the output mirrors the manifest on disk.
        """
        prefix = "  - " if first else "    "
        if isinstance(value, list):
            self.info(f"{prefix}[blue]{markup_escape(key)}:[/blue]")
            for item in value:
                self.info(f"      - {markup_escape(item)}")
        else:
            self.info(
                f"{prefix}[blue]{markup_escape(key)}:[/blue] {markup_escape(value)}"
            )

    def warning(self, msg: object, *args: Any, **kwargs: Any) -> None:
        """Log warning."""
        super().warning(
            f"[bold bright_yellow]{markup_escape(str(msg))}[/bold bright_yellow]",
            *args,
            **kwargs,
        )

    def error(self, msg: object, *args: Any, **kwargs: Any) -> None:
        """Log error."""
        super().error(f"[red]{markup_escape(str(msg))}[/red]", *args, **kwargs)

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
            safe_name = markup_escape(name)
            self.info(f"  [bold][bright_green]{safe_name}:[/bright_green][/bold]")
            DLogger._printed_projects.add(name)

        return Status(
            f"[bold bright_blue]> {markup_escape(message)}[/bold bright_blue]",
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

        line = markup_escape(record.getMessage()).replace("\n", "\n    ")
        record.msg = f"{self.prefix}[{color}]{line}[/{color}]"
        record.args = ()
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
    # Ensure the external logger is a plain Logger so its log methods do not
    # wrap messages in Rich markup (which DLogger.warning / DLogger.error do).
    # Without this, markup_escape in ExtLogFilter would turn those Rich tags
    # into literal text that shifts tab-stop calculations when rendered.
    logger.__class__ = logging.Logger
    logger.setLevel(level)
    logger.propagate = True
    logger.handlers.clear()
    logger.addFilter(ExtLogFilter())
    # Some packages (e.g. patch_ng) cache logger bound-methods as module-level
    # names at import time (e.g. `warning = logger.warning`).  After the
    # __class__ reassignment above those cached references still point at the
    # old DLogger method, so re-bind them to the freshly demoted logger.
    module = sys.modules.get(name.split(".")[0])
    if module is not None:
        for method_name in ("debug", "info", "warning", "error", "critical"):
            attr = getattr(module, method_name, None)
            if isinstance(attr, types.MethodType) and attr.__self__ is logger:
                setattr(module, method_name, getattr(logger, method_name))
