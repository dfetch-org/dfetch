# mypy: ignore-errors
"""Tests for dfetch.util.github_version_check."""

import json
import urllib.error
from unittest.mock import MagicMock, patch

from dfetch.util.github_version_check import newer_version_available

_PATCH_BUILD_OPENER = "dfetch.util.github_version_check.urllib.request.build_opener"


def _fake_response(tag_name: str) -> MagicMock:
    body = json.dumps({"tag_name": tag_name}).encode()
    mock = MagicMock()
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    mock.read = lambda: body
    return mock


def _fake_response_raw(body: bytes) -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    mock.read = lambda: body
    return mock


def _make_opener(response: MagicMock) -> MagicMock:
    opener = MagicMock()
    opener.open.return_value = response
    return MagicMock(return_value=opener)


def _make_opener_error(error: Exception) -> MagicMock:
    opener = MagicMock()
    opener.open.side_effect = error
    return MagicMock(return_value=opener)


@patch(_PATCH_BUILD_OPENER)
@patch("dfetch.util.github_version_check.__version__", "0.13.0")
def test_newer_version_available_returns_version_when_newer(mock_build_opener):
    """A newer tag on GitHub is returned."""
    mock_build_opener.return_value = _make_opener(
        _fake_response("v0.14.0")
    ).return_value

    assert newer_version_available() == "0.14.0"


@patch(_PATCH_BUILD_OPENER)
@patch("dfetch.util.github_version_check.__version__", "0.13.0")
def test_newer_version_available_returns_none_when_current_is_latest(mock_build_opener):
    """No update is signalled when running the latest release."""
    mock_build_opener.return_value = _make_opener(
        _fake_response("v0.13.0")
    ).return_value

    assert newer_version_available() is None


@patch(_PATCH_BUILD_OPENER)
@patch("dfetch.util.github_version_check.__version__", "0.14.0")
def test_newer_version_available_returns_none_when_running_newer_than_release(
    mock_build_opener,
):
    """Pre-release or dev builds newer than the latest tag are not flagged."""
    mock_build_opener.return_value = _make_opener(
        _fake_response("v0.13.0")
    ).return_value

    assert newer_version_available() is None


@patch(_PATCH_BUILD_OPENER)
def test_newer_version_available_returns_none_on_network_error(mock_build_opener):
    """Network failures are swallowed silently."""
    mock_build_opener.return_value = _make_opener_error(
        urllib.error.URLError("timeout")
    ).return_value

    assert newer_version_available() is None


@patch(_PATCH_BUILD_OPENER)
def test_newer_version_available_returns_none_on_bad_json(mock_build_opener):
    """Malformed JSON responses are swallowed silently."""
    mock_build_opener.return_value = _make_opener(
        _fake_response_raw(b"not json {")
    ).return_value

    assert newer_version_available() is None


@patch(_PATCH_BUILD_OPENER)
def test_newer_version_missing_tag_name_returns_none(mock_build_opener):
    """A response without a tag_name key is silently ignored."""
    mock_build_opener.return_value = _make_opener(
        _fake_response_raw(b'{"some_other_key": "x"}')
    ).return_value

    assert newer_version_available() is None


@patch(_PATCH_BUILD_OPENER)
def test_newer_version_empty_tag_name_returns_none(mock_build_opener):
    """An empty tag_name string is silently ignored."""
    mock_build_opener.return_value = _make_opener(
        _fake_response_raw(b'{"tag_name": ""}')
    ).return_value

    assert newer_version_available() is None


@patch(_PATCH_BUILD_OPENER)
def test_newer_version_non_string_tag_name_returns_none(mock_build_opener):
    """Non-string tag_name values (integer or null) are silently ignored."""
    mock_build_opener.return_value = _make_opener(
        _fake_response_raw(b'{"tag_name": 123}')
    ).return_value
    assert newer_version_available() is None

    mock_build_opener.return_value = _make_opener(
        _fake_response_raw(b'{"tag_name": null}')
    ).return_value
    assert newer_version_available() is None
