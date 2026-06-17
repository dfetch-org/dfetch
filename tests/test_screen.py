"""Tests for dfetch.terminal.screen."""

# mypy: ignore-errors
# flake8: noqa

from io import StringIO
from unittest.mock import patch

import pytest

from dfetch.terminal.screen import Screen, erase_last_line

# ---------------------------------------------------------------------------
# erase_last_line
# ---------------------------------------------------------------------------


def test_erase_last_line_writes_ansi_when_tty():
    """erase_last_line writes the ANSI erase sequence when stdout is a TTY."""
    buf = StringIO()
    with patch("dfetch.terminal.screen.is_tty", return_value=True):
        with patch("sys.stdout", buf):
            erase_last_line()
    assert "\x1b[1A\x1b[2K" in buf.getvalue()


def test_erase_last_line_noop_when_not_tty():
    """erase_last_line writes nothing when not a TTY."""
    buf = StringIO()
    with patch("dfetch.terminal.screen.is_tty", return_value=False):
        with patch("sys.stdout", buf):
            erase_last_line()
    assert buf.getvalue() == ""


# ---------------------------------------------------------------------------
# Screen
# ---------------------------------------------------------------------------


def test_screen_initial_draw_does_not_emit_move_up():
    """First draw must not emit the cursor-up escape sequence."""
    screen = Screen()
    buf = StringIO()
    with patch("sys.stdout", buf):
        screen.draw(["hello", "world"])
    output = buf.getvalue()
    assert "\x1b[2A" not in output
    assert "hello\nworld\n" in output


def test_screen_second_draw_emits_move_up():
    """Second draw must move the cursor up by the number of previously drawn lines."""
    screen = Screen()
    buf = StringIO()
    with patch("sys.stdout", buf):
        screen.draw(["line1"])
        screen.draw(["line2"])
    output = buf.getvalue()
    assert "\x1b[1A\x1b[0J" in output


def test_screen_draw_updates_line_count():
    """draw() updates _line_count to the number of lines just written."""
    screen = Screen()
    buf = StringIO()
    with patch("sys.stdout", buf):
        screen.draw(["a", "b", "c"])
    assert screen._line_count == 3


def test_screen_clear_emits_move_up_when_content_present():
    """clear() must erase previously drawn content."""
    screen = Screen()
    buf = StringIO()
    with patch("sys.stdout", buf):
        screen.draw(["one", "two"])
        screen.clear()
    output = buf.getvalue()
    assert "\x1b[2A\x1b[0J" in output


def test_screen_clear_resets_line_count():
    """clear() sets _line_count back to 0."""
    screen = Screen()
    buf = StringIO()
    with patch("sys.stdout", buf):
        screen.draw(["a", "b"])
        screen.clear()
    assert screen._line_count == 0


def test_screen_clear_noop_when_no_content():
    """clear() on an empty screen emits nothing extra beyond the previous draw."""
    screen = Screen()
    buf = StringIO()
    with patch("sys.stdout", buf):
        screen.clear()
    assert buf.getvalue() == ""
