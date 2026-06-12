"""Tests for dfetch.project.svnsubproject.SvnSubProject._fetch_externals."""

# mypy: ignore-errors
# flake8: noqa

from unittest.mock import patch

from dfetch.manifest.project import ProjectEntry
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
