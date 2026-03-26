"""Unit tests for SvnRepo.export() argument safety."""

# mypy: ignore-errors
# flake8: noqa

import pytest
from unittest.mock import patch

from dfetch.vcs.svn import SvnRepo


def test_export_with_revision_passes_correct_args():
    """export() must pass --revision and the digit as adjacent list elements."""
    with patch("dfetch.vcs.svn.run_on_cmdline") as mock_run:
        SvnRepo.export("svn://example.com/repo", rev="12345", dst="/tmp/out")
        cmd = mock_run.call_args[0][1]
        idx = cmd.index("--revision")
        assert cmd[idx + 1] == "12345"


def test_export_without_revision_omits_revision_args():
    """export() with no revision must omit --revision entirely."""
    with patch("dfetch.vcs.svn.run_on_cmdline") as mock_run:
        SvnRepo.export("svn://example.com/repo", dst="/tmp/out")
        assert "--revision" not in mock_run.call_args[0][1]


def test_export_rejects_non_digit_revision():
    """Space-containing or flag-like revision strings must be rejected.

    Before the fix, passing rev='--revision 12345' would be split on spaces and
    inject '--revision' and '12345' as separate SVN arguments, allowing option
    injection by any caller that bypasses the digit-only validation in
    svnsubproject.py.
    """
    with patch("dfetch.vcs.svn.run_on_cmdline"):
        with pytest.raises((ValueError, TypeError)):
            SvnRepo.export("svn://example.com/repo", rev="--revision 12345")
