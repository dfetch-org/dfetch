"""Unit tests for SvnRepo.export() argument safety."""

from unittest.mock import patch

import pytest

from dfetch.vcs.svn import SvnRepo, _match_auto_props_eol_style


def test_export_with_revision_passes_correct_args():
    """export() must produce the exact expected SVN command."""
    with patch("dfetch.vcs.svn.run_on_cmdline") as mock_run:
        SvnRepo.export("svn://example.com/repo", rev="12345", dst="/tmp/out")
        mock_run.assert_called_once()
        assert mock_run.call_args[0][1] == [
            "svn",
            "--non-interactive",
            "export",
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
            "--non-interactive",
            "export",
            "--force",
            "svn://example.com/repo",
            "/tmp/out",
        ]


def test_export_with_native_eol_passes_correct_args():
    """export() with a native eol must pass --native-eol to svn."""
    with patch("dfetch.vcs.svn.run_on_cmdline") as mock_run:
        SvnRepo.export("svn://example.com/repo", dst="/tmp/out", native_eol="LF")
        mock_run.assert_called_once()
        assert mock_run.call_args[0][1] == [
            "svn",
            "--non-interactive",
            "export",
            "--force",
            "--native-eol",
            "LF",
            "svn://example.com/repo",
            "/tmp/out",
        ]


def test_export_rejects_invalid_native_eol():
    """Only LF and CRLF are valid native eol values; never invoke svn otherwise."""
    with patch("dfetch.vcs.svn.run_on_cmdline") as mock_run:
        with pytest.raises(ValueError):
            SvnRepo.export("svn://example.com/repo", native_eol="--something")
        mock_run.assert_not_called()


@pytest.mark.parametrize(
    "name, props, filename, expected",
    [
        ("global rule", "* = svn:eol-style=LF", "any.txt", "LF"),
        ("propget path prefix", ". - * = svn:eol-style=CRLF", "any.txt", "CRLF"),
        ("extension match", "*.bat = svn:eol-style=CRLF", "run.bat", "CRLF"),
        ("extension mismatch", "*.bat = svn:eol-style=CRLF", "run.sh", None),
        (
            "last match wins",
            "* = svn:eol-style=LF\n*.bat = svn:eol-style=CRLF",
            "run.bat",
            "CRLF",
        ),
        (
            "multiple props per pattern",
            "* = svn:keywords=Id;svn:eol-style=LF",
            "a.c",
            "LF",
        ),
        ("no eol-style prop", "* = svn:keywords=Id", "a.c", None),
        ("empty props", "", "a.c", None),
    ],
)
def test_match_auto_props_eol_style(name, props, filename, expected):
    """Auto-props patterns must resolve to the correct svn:eol-style."""
    assert _match_auto_props_eol_style(props, filename) == expected, name


def test_eol_style_for_maps_to_lowercase(tmp_path):
    """eol_style_for must translate svn:eol-style to 'lf'/'crlf'."""
    with patch("dfetch.vcs.svn.run_on_cmdline") as mock_run:
        mock_run.return_value.stdout = b". - * = svn:eol-style=LF"
        assert SvnRepo(tmp_path).eol_style_for("ext/mylib/_") == "lf"


def test_eol_style_for_native_gives_no_preference(tmp_path):
    """svn:eol-style=native means platform default, not a dfetch preference."""
    with patch("dfetch.vcs.svn.run_on_cmdline") as mock_run:
        mock_run.return_value.stdout = b". - * = svn:eol-style=native"
        assert SvnRepo(tmp_path).eol_style_for("ext/mylib/_") is None


def test_eol_style_for_without_svn_returns_none(tmp_path):
    """A missing svn binary must not break the update."""
    with patch(
        "dfetch.vcs.svn.run_on_cmdline",
        side_effect=RuntimeError("svn not available on system, please install"),
    ):
        assert SvnRepo(tmp_path).eol_style_for("ext/mylib/_") is None


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
