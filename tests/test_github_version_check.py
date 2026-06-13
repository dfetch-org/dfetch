# mypy: ignore-errors
"""Tests for dfetch.util.github_version_check."""

import json
import urllib.error
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from dfetch.util.github_version_check import newer_version_available


def _fake_response(tag_name: str) -> MagicMock:
    body = json.dumps({"tag_name": tag_name}).encode()
    mock = MagicMock()
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    mock.read = lambda: body
    return mock


@patch("dfetch.util.github_version_check.urllib.request.urlopen")
@patch("dfetch.util.github_version_check.__version__", "0.13.0")
def test_newer_version_available_returns_version_when_newer(mock_urlopen):
    """A newer tag on GitHub is returned."""
    mock_urlopen.return_value = _fake_response("v0.14.0")

    result = newer_version_available()

    assert result == "0.14.0"


@patch("dfetch.util.github_version_check.urllib.request.urlopen")
@patch("dfetch.util.github_version_check.__version__", "0.13.0")
def test_newer_version_available_returns_none_when_current_is_latest(mock_urlopen):
    """No update is signalled when running the latest release."""
    mock_urlopen.return_value = _fake_response("v0.13.0")

    assert newer_version_available() is None


@patch("dfetch.util.github_version_check.urllib.request.urlopen")
@patch("dfetch.util.github_version_check.__version__", "0.14.0")
def test_newer_version_available_returns_none_when_running_newer_than_release(
    mock_urlopen,
):
    """Pre-release or dev builds newer than the latest tag are not flagged."""
    mock_urlopen.return_value = _fake_response("v0.13.0")

    assert newer_version_available() is None


@patch("dfetch.util.github_version_check.urllib.request.urlopen")
def test_newer_version_available_returns_none_on_network_error(mock_urlopen):
    """Network failures are swallowed silently."""
    mock_urlopen.side_effect = urllib.error.URLError("timeout")

    assert newer_version_available() is None


@patch("dfetch.util.github_version_check.urllib.request.urlopen")
def test_newer_version_available_returns_none_on_bad_json(mock_urlopen):
    """Malformed JSON responses are swallowed silently."""
    mock = MagicMock()
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    mock.read = lambda: b"not json {"
    mock_urlopen.return_value = mock

    assert newer_version_available() is None
