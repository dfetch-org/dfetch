"""Tests for dfetch/commands/diff.py."""

# mypy: ignore-errors
# flake8: noqa

import argparse
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from dfetch.commands.diff import Diff
from dfetch.project.superproject import NoVcsSuperProject
from tests.manifest_mock import mock_manifest


def _make_args(projects=None, revs=""):
    args = argparse.Namespace()
    args.projects = projects or ["myproj"]
    args.revs = revs
    return args


# ---------- Static helper tests (no I/O) ----------

def test_parse_revs_empty_string():
    """Empty string returns ('', '')."""
    assert Diff._parse_revs("") == ("", "")


def test_parse_revs_single_rev():
    """A single hash returns (hash, '')."""
    assert Diff._parse_revs("abc123") == ("abc123", "")


def test_parse_revs_two_revs():
    """Two hashes separated by ':' returns (old, new)."""
    assert Diff._parse_revs("abc:def") == ("abc", "def")


def test_parse_revs_with_leading_colon():
    """A leading colon is stripped, returning the single rev as the old rev."""
    assert Diff._parse_revs(":abc") == ("abc", "")


def test_rev_msg_with_new_rev():
    """When new_rev is provided the message is 'from X to Y'."""
    assert Diff._rev_msg("old", "new") == "from old to new"


def test_rev_msg_without_new_rev():
    """When new_rev is absent the message is 'since X'."""
    assert Diff._rev_msg("old", "") == "since old"


# ---------- Diff.__call__ tests ----------

def _make_superproject(manifest, is_novcs=False):
    if is_novcs:
        superproject = Mock(spec=NoVcsSuperProject)
    else:
        superproject = Mock()
    superproject.manifest = manifest
    superproject.root_directory = Path("/tmp")
    return superproject


def test_diff_raises_for_novcs_superproject():
    """Diff raises RuntimeError immediately when the superproject has no VCS."""
    diff = Diff()
    manifest = mock_manifest([{"name": "myproj"}])
    superproject = _make_superproject(manifest, is_novcs=True)

    with patch("dfetch.commands.diff.create_super_project", return_value=superproject):
        with pytest.raises(RuntimeError, match="SVN or Git"):
            diff(_make_args())


def test_diff_project_no_destination_raises():
    """RuntimeError is raised when the project destination does not exist on disk."""
    diff = Diff()
    manifest = mock_manifest([{"name": "myproj"}])
    superproject = _make_superproject(manifest)
    superproject.manifest = manifest

    with patch("dfetch.commands.diff.create_super_project", return_value=superproject):
        with patch("dfetch.commands.diff.in_directory"):
            with patch("os.path.exists", return_value=False):
                with pytest.raises(RuntimeError):
                    diff(_make_args(revs="abc123"))


def test_diff_project_no_old_rev_raises():
    """RuntimeError is raised when no old rev can be determined."""
    diff = Diff()
    manifest = mock_manifest([{"name": "myproj"}])
    superproject = _make_superproject(manifest)

    mock_sub = Mock()
    mock_sub.metadata_path = "/tmp/myproj/.dfetch_data.yaml"
    mock_sub.local_path = "/tmp/myproj"
    superproject.get_sub_project.return_value = mock_sub
    superproject.get_file_revision.return_value = ""

    with patch("dfetch.commands.diff.create_super_project", return_value=superproject):
        with patch("dfetch.commands.diff.in_directory"):
            with patch("os.path.exists", return_value=True):
                with pytest.raises(RuntimeError):
                    diff(_make_args(revs=""))


def test_diff_project_writes_patch_file():
    """When superproject.diff returns patch content, it is written to a .patch file."""
    diff = Diff()
    manifest = mock_manifest([{"name": "myproj"}])
    superproject = _make_superproject(manifest)

    mock_sub = Mock()
    mock_sub.metadata_path = "/tmp/myproj/.dfetch_data.yaml"
    mock_sub.local_path = "/tmp/myproj"
    superproject.get_sub_project.return_value = mock_sub
    superproject.get_file_revision.return_value = "deadbeef"
    superproject.diff.return_value = "diff --git a/file b/file\n"

    with patch("dfetch.commands.diff.create_super_project", return_value=superproject):
        with patch("dfetch.commands.diff.in_directory"):
            with patch("os.path.exists", return_value=True):
                with patch("pathlib.Path.write_text") as mock_write:
                    diff(_make_args(revs="deadbeef"))

                    mock_write.assert_called_once()


def test_diff_project_no_diff_logs_info():
    """When superproject.diff returns empty string, info is logged about no diffs."""
    diff = Diff()
    manifest = mock_manifest([{"name": "myproj"}])
    superproject = _make_superproject(manifest)

    mock_sub = Mock()
    mock_sub.metadata_path = "/tmp/myproj/.dfetch_data.yaml"
    mock_sub.local_path = "/tmp/myproj"
    superproject.get_sub_project.return_value = mock_sub
    superproject.get_file_revision.return_value = "deadbeef"
    superproject.diff.return_value = ""

    with patch("dfetch.commands.diff.create_super_project", return_value=superproject):
        with patch("dfetch.commands.diff.in_directory"):
            with patch("os.path.exists", return_value=True):
                with patch("dfetch.commands.diff.logger") as mock_logger:
                    diff(_make_args(revs="deadbeef"))

                    mock_logger.print_info_line.assert_called_once()
                    call_args = mock_logger.print_info_line.call_args[0]
                    assert "No diffs found" in call_args[1]
