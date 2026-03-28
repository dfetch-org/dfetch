"""Single-line ghost prompt."""

import sys

from rich.console import Console
from rich.prompt import Prompt

from dfetch.terminal.ansi import DIM, GREEN, RESET
from dfetch.terminal.keys import is_tty, read_key
from dfetch.terminal.types import Entry

_console = Console()

_PROMPT_FORMAT = "  [green]?[/green] [bold]{label}[/bold]"


def _ghost_handle_backspace(buf: list[str], ghost_active: bool, ghost_len: int) -> bool:
    """Handle backspace in a ghost prompt; returns updated *ghost_active*."""
    if buf:
        buf.pop()
        sys.stdout.write("\x1b[1D\x1b[K")
        sys.stdout.flush()
    elif ghost_active:
        sys.stdout.write(f"\x1b[{ghost_len}D\x1b[K")
        sys.stdout.flush()
        return False
    return ghost_active


def _ghost_handle_char(
    ch: str, buf: list[str], ghost_active: bool, ghost_len: int
) -> bool:
    """Append *ch* to *buf*, clearing ghost if still active; returns updated *ghost_active*."""
    if ghost_active:
        sys.stdout.write(f"\x1b[{ghost_len}D\x1b[K{ch}")
        ghost_active = False
    else:
        sys.stdout.write(ch)
    sys.stdout.flush()
    buf.append(ch)
    return ghost_active


def ghost_prompt(label: str, default: str = "") -> str:  # pragma: no cover
    """Single-line prompt with *default* shown as dim ghost text.

    The ghost disappears the moment the user types anything.
    Pressing Enter with no input accepts *default*.
    """
    sys.stdout.write(f"{label}: {DIM}{default}{RESET}")
    sys.stdout.flush()

    buf: list[str] = []
    ghost_active = bool(default)

    while True:
        key = read_key()
        if key == "ENTER":
            sys.stdout.write("\n")
            sys.stdout.flush()
            return "".join(buf) if buf else default
        if key in ("\x7f", "\x08"):
            ghost_active = _ghost_handle_backspace(buf, ghost_active, len(default))
            continue
        ch = " " if key == "SPACE" else key
        if len(ch) == 1 and ch.isprintable():
            ghost_active = _ghost_handle_char(ch, buf, ghost_active, len(default))


def numbered_prompt(
    entries: list[Entry],
    label: str,
    hint: str,
    default: str = "",
    note: str = "",
) -> str:
    """Display *entries* then prompt until the user picks one or types freely.

    Each entry is printed as ``  N  <display>`` where *N* is its 1-based
    index.  An optional *note* line (e.g. a truncation message) is printed
    after the entries without a number.

    If the user enters a digit in ``[1, len(entries)]`` returns the
    corresponding ``entry.value``.  Any other non-empty input is returned
    as-is.  Out-of-range numbers loop with a warning.
    """
    for i, entry in enumerate(entries, start=1):
        _console.print(f"  [bold white]{i:>2}[/bold white]  {entry.display}")
    if note:
        _console.print(note)

    n = len(entries)
    while True:
        raw = Prompt.ask(
            _PROMPT_FORMAT.format(label=label) + f"  ({hint})",
            default=default,
        ).strip()

        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < n:
                return entries[idx].value
            _console.print(f"  [dim]Pick a number between 1 and {n}.[/dim]")
            continue

        return raw


def prompt(label: str, default: str = "") -> str:
    """Single-line prompt that adapts to the terminal environment.

    In a TTY shows ghost text via :func:`ghost_prompt`.
    Outside a TTY (CI, pipe, tests) uses a Rich fallback.
    """
    if is_tty():
        return ghost_prompt(f"  {GREEN}?{RESET} {label}", default).strip()
    return Prompt.ask(_PROMPT_FORMAT.format(label=label), default=default).strip()
