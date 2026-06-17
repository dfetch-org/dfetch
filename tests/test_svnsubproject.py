"""Tests for dfetch.project.svnsubproject.SvnSubProject._fetch_externals."""

# mypy: ignore-errors
# flake8: noqa

from unittest.mock import Mock, patch

import pytest

from dfetch.manifest.project import ProjectEntry
from dfetch.manifest.version import Version
from dfetch.project.svnsubproject import SvnSubProject
from dfetch.vcs.svn import External

REPO_ROOT = "repo-root"


def test_fetch_externals_returns_empty_when_no_externals():
    with patch("dfetch.project.svnsubproject.SvnRepo.externals_from_url") as mock_ext:
        mock_ext.return_value = []
        subproject = SvnSubProject(
            ProjectEntry({"name": "myproject", "url": REPO_ROOT})
        )
        assert subproject._fetch_externals(REPO_ROOT + "/trunk", "42") == []


def test_fetch_externals_forwards_path_and_revision():
    with patch("dfetch.project.svnsubproject.SvnRepo.externals_from_url") as mock_ext:
        mock_ext.return_value = []
        subproject = SvnSubProject(
            ProjectEntry({"name": "myproject", "url": REPO_ROOT})
        )
        complete_path = REPO_ROOT + "/trunk"
        subproject._fetch_externals(complete_path, "77")
        mock_ext.assert_called_once_with(complete_path, "77")


def test_fetch_externals_maps_externals_to_dependencies():
    externals_list = [
        External(
            name="mylib",
            toplevel="",
            path="vendor/mylib",
            revision="100",
            url=REPO_ROOT + "/libs",
            branch="",
            tag="",
            src="",
        ),
        External(
            name="utils",
            toplevel="",
            path="vendor/utils",
            revision="200",
            url=REPO_ROOT + "/utils",
            branch="devel",
            tag="",
            src="",
        ),
    ]
    with patch("dfetch.project.svnsubproject.SvnRepo.externals_from_url") as mock_ext:
        mock_ext.return_value = externals_list
        subproject = SvnSubProject(
            ProjectEntry({"name": "myproject", "url": REPO_ROOT})
        )
        result = subproject._fetch_externals(REPO_ROOT + "/trunk", "100")

        assert len(result) == 2

        assert result[0]["remote_url"] == REPO_ROOT + "/libs"
        assert result[0]["destination"] == "vendor/mylib"
        assert result[0]["branch"] == ""
        assert result[0]["tag"] == ""
        assert result[0]["revision"] == "100"
        assert result[0]["source_type"] == "svn-external"

        assert result[1]["remote_url"] == REPO_ROOT + "/utils"
        assert result[1]["destination"] == "vendor/utils"
        assert result[1]["branch"] == "devel"
        assert result[1]["revision"] == "200"
        assert result[1]["source_type"] == "svn-external"


def test_fetch_externals_preserves_tag_in_dependency():
    external = External(
        name="mylib",
        toplevel="",
        path="vendor/mylib",
        revision="300",
        url=REPO_ROOT + "/libs",
        branch="",
        tag="v2.0",
        src="",
    )
    with patch("dfetch.project.svnsubproject.SvnRepo.externals_from_url") as mock_ext:
        mock_ext.return_value = [external]
        subproject = SvnSubProject(
            ProjectEntry({"name": "myproject", "url": REPO_ROOT})
        )
        result = subproject._fetch_externals(REPO_ROOT + "/trunk", "300")

        assert result[0]["tag"] == "v2.0"
        assert result[0]["source_type"] == "svn-external"


def test_fetch_externals_nonstd_layout_preserves_space_branch():
    # A non-standard-layout external (URL contains no /trunk/, /branches/, or
    # /tags/) is represented with branch=" " by _split_url.  That sentinel must
    # reach the Dependency unchanged — it must NOT be collapsed to "" or "trunk"
    # by the display_branch substitution that only applies to the log line.
    external = External(
        name="Database",
        toplevel="",
        path="./Database",
        revision="",
        url="http://svn.mycompany.eu/MYCOMPANY/SomeModule/Core/Modules/Database",
        branch=" ",
        tag="",
        src="",
    )
    with patch("dfetch.project.svnsubproject.SvnRepo.externals_from_url") as mock_ext:
        mock_ext.return_value = [external]
        subproject = SvnSubProject(
            ProjectEntry({"name": "myproject", "url": REPO_ROOT})
        )
        result = subproject._fetch_externals(REPO_ROOT + "/trunk", "")

        assert result[0]["branch"] == " "
        assert result[0]["remote_url"] == (
            "http://svn.mycompany.eu/MYCOMPANY/SomeModule/Core/Modules/Database"
        )


# ---------------------------------------------------------------------------
# SvnSubProject._parse_file_pattern
# ---------------------------------------------------------------------------


def test_parse_file_pattern_no_glob_returns_path_unchanged():
    path, glob = SvnSubProject._parse_file_pattern("svn://example.com/repo/trunk")
    assert path == "svn://example.com/repo/trunk"
    assert glob == ""


def test_parse_file_pattern_single_glob_splits_correctly():
    path, glob = SvnSubProject._parse_file_pattern(
        "svn://example.com/repo/trunk/src/*.h"
    )
    assert path == "svn://example.com/repo/trunk/src"
    assert glob == "*.h"


def test_parse_file_pattern_multiple_globs_raises():
    with pytest.raises(RuntimeError, match="single"):
        SvnSubProject._parse_file_pattern("svn://example.com/repo/trunk/src/*.*/")


def test_parse_file_pattern_glob_with_suffix():
    path, glob = SvnSubProject._parse_file_pattern(
        "svn://example.com/repo/trunk/src/lib*.so"
    )
    assert path == "svn://example.com/repo/trunk/src"
    assert glob == "lib*.so"


# ---------------------------------------------------------------------------
# SvnSubProject._determine_what_to_fetch
# ---------------------------------------------------------------------------


def _make_svn_subproject(url: str = "svn://example.com/repo") -> SvnSubProject:
    with patch("dfetch.project.svnsubproject.SvnRemote"):
        return SvnSubProject(ProjectEntry({"name": "myproject", "url": url}))


def test_determine_what_to_fetch_tag_sets_branch_path():
    subproject = _make_svn_subproject()
    version = Version(tag="v1.0")

    with patch.object(subproject, "_get_revision", return_value="42"):
        branch, branch_path, revision = subproject._determine_what_to_fetch(version)

    assert branch == ""
    assert "tags/v1.0" in branch_path
    assert revision == "42"


def test_determine_what_to_fetch_non_std_layout_branch():
    subproject = _make_svn_subproject()
    version = Version(branch=" ")

    with patch.object(subproject, "_get_revision", return_value="10"):
        branch, branch_path, revision = subproject._determine_what_to_fetch(version)

    assert branch == " "
    assert branch_path == ""
    assert revision == "10"


def test_determine_what_to_fetch_trunk_branch():
    subproject = _make_svn_subproject()
    version = Version(branch="trunk")

    with patch.object(subproject, "_get_revision", return_value="5"):
        branch, branch_path, revision = subproject._determine_what_to_fetch(version)

    assert branch == "trunk"
    assert branch_path == "trunk"
    assert revision == "5"


def test_determine_what_to_fetch_feature_branch():
    subproject = _make_svn_subproject()
    version = Version(branch="feature-x")

    with patch.object(subproject, "_get_revision", return_value="99"):
        branch, branch_path, revision = subproject._determine_what_to_fetch(version)

    assert branch == "feature-x"
    assert "branches/feature-x" in branch_path
    assert revision == "99"


def test_determine_what_to_fetch_provided_revision_skips_remote_call():
    subproject = _make_svn_subproject()
    version = Version(branch="trunk", revision="77")

    with patch.object(subproject, "_get_revision") as mock_get_rev:
        branch, branch_path, revision = subproject._determine_what_to_fetch(version)
        mock_get_rev.assert_not_called()

    assert revision == "77"


def test_determine_what_to_fetch_non_digit_revision_raises():
    subproject = _make_svn_subproject()
    version = Version(branch="trunk")

    with patch.object(subproject, "_get_revision", return_value="HEAD"):
        with pytest.raises(RuntimeError, match="must be a number"):
            subproject._determine_what_to_fetch(version)


# ---------------------------------------------------------------------------
# SvnSubProject.check and other properties
# ---------------------------------------------------------------------------


def test_check_delegates_to_remote_repo():
    with patch("dfetch.project.svnsubproject.SvnRemote") as mock_remote_cls:
        mock_remote_cls.return_value.is_svn.return_value = True
        subproject = SvnSubProject(
            ProjectEntry({"name": "myproject", "url": "svn://example.com/repo"})
        )
        assert subproject.check() is True


def test_revision_is_enough_returns_false():
    assert SvnSubProject.revision_is_enough() is False


def test_latest_revision_on_trunk_uses_trunk():
    subproject = _make_svn_subproject()

    with patch.object(subproject, "_get_revision", return_value="50") as mock_rev:
        result = subproject._latest_revision_on_branch("trunk")
        mock_rev.assert_called_once_with("trunk")

    assert result == "50"


def test_latest_revision_on_feature_branch_uses_branches_prefix():
    subproject = _make_svn_subproject()

    with patch.object(subproject, "_get_revision", return_value="60") as mock_rev:
        result = subproject._latest_revision_on_branch("feature-y")
        mock_rev.assert_called_once_with("branches/feature-y")

    assert result == "60"


def test_list_of_branches_includes_trunk():
    with patch("dfetch.project.svnsubproject.SvnRemote") as mock_remote_cls:
        mock_remote_cls.return_value.list_of_branches.return_value = ["feature-a"]
        subproject = SvnSubProject(
            ProjectEntry({"name": "myproject", "url": "svn://example.com/repo"})
        )
        branches = subproject.list_of_branches()

    assert "trunk" in branches
    assert "feature-a" in branches
