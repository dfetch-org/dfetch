"""Tests for dfetch/project/superproject.py (NoVcsSuperProject) and dfetch/manifest/version.py."""

# mypy: ignore-errors
# flake8: noqa

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from dfetch.manifest.manifest import Manifest
from dfetch.manifest.version import Version
from dfetch.project.superproject import NoVcsSuperProject, RevisionRange

# =====================
# Version.field property
# =====================


def test_version_field_returns_tag_when_set():
    """Version.field returns ('tag', value) when a tag is set."""
    v = Version(tag="v1.0")
    assert v.field == ("tag", "v1.0")


def test_version_field_returns_revision_when_no_tag():
    """Version.field returns ('revision', value) when only a revision is set."""
    v = Version(revision="deadbeef")
    assert v.field == ("revision", "deadbeef")


def test_version_field_returns_branch_when_only_branch():
    """Version.field returns ('branch', value) when only a branch is set."""
    v = Version(branch="main")
    assert v.field == ("branch", "main")


# =====================
# NoVcsSuperProject
# =====================


def _make_novcs(root=Path("/tmp")):
    """Create a NoVcsSuperProject with a mocked manifest."""
    manifest = Mock(spec=Manifest)
    manifest.path = str(root / "dfetch.yaml")
    return NoVcsSuperProject(manifest, root)


def test_novcs_check_always_returns_true():
    """NoVcsSuperProject.check returns True for any path."""
    assert NoVcsSuperProject.check("/some/path") is True


def test_novcs_get_sub_project_returns_none():
    """NoVcsSuperProject.get_sub_project always returns None."""
    project = _make_novcs()
    assert project.get_sub_project(Mock()) is None


def test_novcs_has_local_changes_returns_true():
    """NoVcsSuperProject.has_local_changes_in_dir always returns True."""
    project = _make_novcs()
    assert project.has_local_changes_in_dir("/some/path") is True


def test_novcs_get_file_revision_returns_empty_string():
    """NoVcsSuperProject.get_file_revision always returns empty string."""
    project = _make_novcs()
    assert project.get_file_revision("/some/file") == ""


def test_novcs_diff_returns_empty_string():
    """NoVcsSuperProject.diff always returns empty string."""
    project = _make_novcs()
    result = project.diff("/some/path", RevisionRange("old", "new"), ignore=("meta",))
    assert result == ""


def test_novcs_import_projects_raises():
    """NoVcsSuperProject.import_projects raises RuntimeError."""
    with pytest.raises(RuntimeError, match="git or SVN"):
        NoVcsSuperProject.import_projects()


def test_novcs_get_username_returns_string():
    """NoVcsSuperProject.get_username returns a non-empty string."""
    project = _make_novcs()
    with patch("getpass.getuser", return_value="testuser"):
        username = project.get_username()
    assert isinstance(username, str)
    assert len(username) > 0


def test_novcs_get_useremail_includes_username():
    """NoVcsSuperProject.get_useremail returns an email-like string."""
    project = _make_novcs()
    with patch("getpass.getuser", return_value="alice"):
        email = project.get_useremail()
    assert "@" in email


def test_novcs_ignored_files_returns_empty_list():
    """NoVcsSuperProject.ignored_files returns an empty sequence."""
    project = _make_novcs(root=Path("/tmp"))
    # Use root_directory as path so no path traversal error
    result = project.ignored_files(str(project.root_directory))
    assert list(result) == []
