"""Unit tests for SvnRepo.export() argument safety."""

from unittest.mock import patch

import pytest

from dfetch.vcs.svn import SvnRepo


def test_export_with_revision_passes_correct_args():
    """export() must produce the exact expected SVN command."""
    with patch("dfetch.vcs.svn.run_on_cmdline") as mock_run:
        SvnRepo.export("svn://example.com/repo", rev="12345", dst="/tmp/out")
        mock_run.assert_called_once()
        assert mock_run.call_args[0][1] == [
            "svn",
            "export",
            "--non-interactive",
            "--force",
            "--revision",
            "12345",
            "svn://example.com/repo",
            "/tmp/out",
        ]


def test_export_without_revision_omits_revision_args():
    """export() with no revision must produce the exact expected SVN command."""
    with patch("dfetch.vcs.svn.run_on_cmdline") as mock_run:
        SvnRepo.export("svn://example.com/repo", dst="/tmp/out")
        mock_run.assert_called_once()
        assert mock_run.call_args[0][1] == [
            "svn",
            "export",
            "--non-interactive",
            "--force",
            "svn://example.com/repo",
            "/tmp/out",
        ]


def test_export_rejects_non_digit_revision():
    """Space-containing or flag-like revision strings must raise ValueError.

    Before the fix, passing rev='--revision 12345' would be split on spaces and
    inject '--revision' and '12345' as separate SVN arguments, allowing option
    injection by any caller that bypasses the digit-only validation in
    svnsubproject.py.  The subprocess must never be invoked for an invalid rev.
    """
    with patch("dfetch.vcs.svn.run_on_cmdline") as mock_run:
        with pytest.raises(ValueError):
            SvnRepo.export("svn://example.com/repo", rev="--revision 12345")
        mock_run.assert_not_called()
