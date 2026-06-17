"""Tests for dfetch.terminal.prompt helper functions."""

# mypy: ignore-errors
# flake8: noqa

from io import StringIO
from unittest.mock import patch

from dfetch.terminal.prompt import _ghost_handle_backspace, _ghost_handle_char


# ---------------------------------------------------------------------------
# _ghost_handle_backspace
# ---------------------------------------------------------------------------


def test_backspace_pops_last_char_from_buf():
    """Backspace removes the last character from the buffer."""
    buf = ["a", "b", "c"]
    buf_out = StringIO()
    with patch("sys.stdout", buf_out):
        result = _ghost_handle_backspace(buf, ghost_active=False, ghost_len=5)
    assert buf == ["a", "b"]
    assert result is False


def test_backspace_when_buf_empty_and_ghost_active_clears_ghost():
    """Backspace with empty buf and ghost active clears the ghost text and returns False."""
    buf = []
    buf_out = StringIO()
    with patch("sys.stdout", buf_out):
        result = _ghost_handle_backspace(buf, ghost_active=True, ghost_len=4)
    assert result is False
    assert "\x1b[4D\x1b[K" in buf_out.getvalue()


def test_backspace_when_buf_empty_and_ghost_inactive_returns_inactive():
    """Backspace with empty buf and ghost already inactive returns False (unchanged)."""
    buf = []
    buf_out = StringIO()
    with patch("sys.stdout", buf_out):
        result = _ghost_handle_backspace(buf, ghost_active=False, ghost_len=4)
    assert result is False
    # No ANSI written for moving back ghost text
    assert "\x1b[4D" not in buf_out.getvalue()


def test_backspace_with_char_in_buf_writes_cursor_left_and_erase():
    """Backspace with a char in buf writes cursor-left and erase-to-end-of-line."""
    buf = ["x"]
    buf_out = StringIO()
    with patch("sys.stdout", buf_out):
        _ghost_handle_backspace(buf, ghost_active=False, ghost_len=3)
    assert "\x1b[1D\x1b[K" in buf_out.getvalue()


def test_backspace_preserves_ghost_active_when_buf_nonempty():
    """Backspace with nonempty buf does not change ghost_active."""
    buf = ["x"]
    buf_out = StringIO()
    with patch("sys.stdout", buf_out):
        result = _ghost_handle_backspace(buf, ghost_active=True, ghost_len=3)
    assert result is True


# ---------------------------------------------------------------------------
# _ghost_handle_char
# ---------------------------------------------------------------------------


def test_handle_char_appends_to_buf():
    """Character is appended to the buffer."""
    buf = []
    buf_out = StringIO()
    with patch("sys.stdout", buf_out):
        _ghost_handle_char("a", buf, ghost_active=False, ghost_len=5)
    assert buf == ["a"]


def test_handle_char_writes_char_when_ghost_inactive():
    """Character is echoed to stdout when ghost is not active."""
    buf = []
    buf_out = StringIO()
    with patch("sys.stdout", buf_out):
        _ghost_handle_char("z", buf, ghost_active=False, ghost_len=5)
    assert "z" in buf_out.getvalue()


def test_handle_char_clears_ghost_on_first_keystroke():
    """When ghost is active, first char clears ghost text before writing char."""
    buf = []
    buf_out = StringIO()
    with patch("sys.stdout", buf_out):
        result = _ghost_handle_char("a", buf, ghost_active=True, ghost_len=3)
    # Ghost should now be inactive
    assert result is False
    output = buf_out.getvalue()
    # The clear sequence contains the cursor-back move
    assert "\x1b[3D\x1b[K" in output
    assert "a" in output


def test_handle_char_returns_false_after_clearing_ghost():
    """_ghost_handle_char returns False once ghost is cleared."""
    buf = []
    buf_out = StringIO()
    with patch("sys.stdout", buf_out):
        result = _ghost_handle_char("x", buf, ghost_active=True, ghost_len=4)
    assert result is False


def test_handle_char_returns_false_when_ghost_already_inactive():
    """_ghost_handle_char returns False when ghost was already inactive."""
    buf = []
    buf_out = StringIO()
    with patch("sys.stdout", buf_out):
        result = _ghost_handle_char("y", buf, ghost_active=False, ghost_len=4)
    assert result is False
