"""Cross-platform raw keypress reading and TTY detection."""

import os
import sys


def is_tty() -> bool:
    """Return True when stdin is an interactive terminal (not CI, not piped)."""
    return sys.stdin.isatty() and not os.environ.get("CI")


def read_key() -> str:  # pragma: no cover – requires live terminal
    """Read one keypress from stdin in raw mode; return a normalised key name.

    Possible return values: ``"UP"``, ``"DOWN"``, ``"LEFT"``, ``"RIGHT"``,
    ``"PGUP"``, ``"PGDN"``, ``"ENTER"``, ``"SPACE"``, ``"ESC"``, or a
    single printable character string.

    Raises ``KeyboardInterrupt`` on Ctrl-C / Ctrl-D.
    """
    if sys.platform == "win32":
        return _read_key_windows()
    return _read_key_unix()


def _read_key_windows() -> str:  # pragma: no cover
    import msvcrt  # type: ignore[import]  # pylint: disable=import-outside-toplevel,import-error

    ch = msvcrt.getwch()  # type: ignore[attr-defined]
    if ch in ("\x00", "\xe0"):
        arrow = {
            "H": "UP",
            "P": "DOWN",
            "K": "LEFT",
            "M": "RIGHT",
            "I": "PGUP",
            "Q": "PGDN",
        }
        return arrow.get(msvcrt.getwch(), "UNKNOWN")  # type: ignore[attr-defined,no-any-return]
    if ch in ("\r", "\n"):
        return "ENTER"
    if ch == "\x1b":
        return "ESC"
    if ch == " ":
        return "SPACE"
    if ch == "\x03":
        raise KeyboardInterrupt
    return str(ch)  # ch is Any from untyped msvcrt


def _read_key_unix() -> str:  # pragma: no cover
    import select as _select  # pylint: disable=import-outside-toplevel
    import termios  # pylint: disable=import-outside-toplevel
    import tty  # pylint: disable=import-outside-toplevel

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = os.read(fd, 1)

        if ch in (b"\r", b"\n"):
            return "ENTER"

        if ch == b"\x1b":
            readable, _, _ = _select.select([fd], [], [], 0.05)
            if readable:
                rest = b""
                while True:
                    more, _, _ = _select.select([fd], [], [], 0.01)
                    if not more:
                        break
                    rest += os.read(fd, 1)
                escape_sequences = {
                    b"\x1b[A": "UP",
                    b"\x1b[B": "DOWN",
                    b"\x1b[C": "RIGHT",
                    b"\x1b[D": "LEFT",
                    b"\x1b[5~": "PGUP",
                    b"\x1b[6~": "PGDN",
                }
                return escape_sequences.get(ch + rest, "ESC")
            return "ESC"

        if ch == b" ":
            return "SPACE"
        if ch in (b"\x03", b"\x04"):
            raise KeyboardInterrupt

        return ch.decode("utf-8", errors="replace")
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
