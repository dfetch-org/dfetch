"""Tests for dfetch.project.svnsuperproject.SvnSuperProject."""

# mypy: ignore-errors
# flake8: noqa

import pathlib
from unittest.mock import MagicMock, Mock, patch

import pytest

from dfetch.manifest.manifest import Manifest
from dfetch.manifest.project import ProjectEntry
from dfetch.project.superproject import RevisionRange
from dfetch.project.svnsuperproject import SvnSuperProject


def _make_superproject(root: str = "/some/root") -> SvnSuperProject:
    """Build a SvnSuperProject with a mocked SvnRepo."""
    manifest = MagicMock(spec=Manifest)
    manifest.path = f"{root}/dfetch.yaml"
    with patch("dfetch.project.svnsuperproject.SvnRepo"):
        return SvnSuperProject(manifest, pathlib.Path(root))


def test_check_returns_true_when_svn_repo():
    with patch("dfetch.project.svnsuperproject.SvnRepo") as mock_repo_cls:
        mock_repo_cls.return_value.is_svn.return_value = True
        assert SvnSuperProject.check("/some/path") is True


def test_check_returns_false_when_not_svn_repo():
    with patch("dfetch.project.svnsuperproject.SvnRepo") as mock_repo_cls:
        mock_repo_cls.return_value.is_svn.return_value = False
        assert SvnSuperProject.check("/some/path") is False


def test_get_sub_project_returns_svn_sub_project():
    superproject = _make_superproject()
    project = ProjectEntry({"name": "mylib", "url": "https://example.com/mylib"})

    with patch("dfetch.project.svnsuperproject.SvnSubProject") as mock_cls:
        result = superproject.get_sub_project(project)
        mock_cls.assert_called_once_with(project)
        assert result == mock_cls.return_value


def test_ignored_files_delegates_to_svn_repo():
    superproject = _make_superproject(root="/repo")

    with patch(
        "dfetch.project.svnsuperproject.resolve_absolute_path",
        return_value=pathlib.Path("/repo/vendor"),
    ):
        with patch("dfetch.project.svnsuperproject.check_no_path_traversal"):
            with patch(
                "dfetch.project.svnsuperproject.SvnRepo.ignored_files",
                return_value=["a.obj"],
            ):
                result = superproject.ignored_files("vendor")

    assert result == ["a.obj"]


def test_has_local_changes_in_dir_returns_true_when_changed():
    superproject = _make_superproject()

    with patch(
        "dfetch.project.svnsuperproject.SvnRepo.any_changes_or_untracked",
        return_value=True,
    ):
        result = superproject.has_local_changes_in_dir("some/path")

    assert result is True


def test_has_local_changes_in_dir_returns_false_when_clean():
    superproject = _make_superproject()

    with patch(
        "dfetch.project.svnsuperproject.SvnRepo.any_changes_or_untracked",
        return_value=False,
    ):
        result = superproject.has_local_changes_in_dir("some/path")

    assert result is False


def test_get_username_returns_repo_username_when_set():
    superproject = _make_superproject()

    with patch.object(superproject, "_repo") as mock_repo:
        mock_repo.get_username.return_value = "alice"
        assert superproject.get_username() == "alice"


def test_get_username_falls_back_when_repo_returns_empty():
    superproject = _make_superproject()

    with patch.object(superproject, "_repo") as mock_repo:
        mock_repo.get_username.return_value = ""
        with patch("getpass.getuser", return_value="bob"):
            result = superproject.get_username()
    assert result == "bob"


def test_get_useremail_always_falls_back():
    superproject = _make_superproject()

    with patch.object(superproject, "get_username", return_value="carol"):
        result = superproject.get_useremail()

    assert result == "carol@example.com"


def test_get_file_revision_delegates_to_repo():
    superproject = _make_superproject()

    with patch.object(superproject, "_repo") as mock_repo:
        mock_repo.get_last_changed_revision.return_value = "42"
        result = superproject.get_file_revision("some/file.txt")

    assert result == "42"


def test_eol_preferences_includes_paths_with_style():
    superproject = _make_superproject()

    with patch.object(superproject, "_repo") as mock_repo:
        mock_repo.eol_style_for.side_effect = lambda p: "lf" if p == "a.txt" else ""
        result = superproject.eol_preferences(["a.txt", "b.bin"])

    assert result == {"a.txt": "lf"}


def test_eol_preferences_empty_when_no_styles():
    superproject = _make_superproject()

    with patch.object(superproject, "_repo") as mock_repo:
        mock_repo.eol_style_for.return_value = ""
        result = superproject.eol_preferences(["a.txt"])

    assert result == {}


def test_diff_with_new_revision_returns_patch_dump():
    superproject = _make_superproject()

    fake_patch = Mock()
    fake_patch.dump.return_value = "diff output"

    with patch("dfetch.project.svnsuperproject.SvnRepo") as mock_repo_cls:
        mock_repo_cls.return_value.create_diff.return_value = fake_patch
        result = superproject.diff(
            "some/path",
            revisions=RevisionRange(old="10", new="20"),
            ignore=(),
        )

    assert result == "diff output"


def test_diff_without_new_revision_extends_with_untracked():
    superproject = _make_superproject()

    fake_patch = Mock()
    fake_patch.dump.return_value = "full patch"

    with patch("dfetch.project.svnsuperproject.SvnRepo") as mock_repo_cls:
        mock_repo_cls.return_value.create_diff.return_value = fake_patch
        mock_repo_cls.return_value.untracked_files.return_value = []
        with patch("dfetch.project.svnsuperproject.in_directory") as mock_indir:
            mock_indir.return_value.__enter__ = Mock(return_value=None)
            mock_indir.return_value.__exit__ = Mock(return_value=False)
            with patch("dfetch.project.svnsuperproject.Patch.for_new_files", return_value=Mock()):
                result = superproject.diff(
                    "some/path",
                    revisions=RevisionRange(old="10", new=""),
                    ignore=(),
                )

    assert result == "full patch"


def test_import_projects_returns_empty_when_no_externals():
    with patch("dfetch.project.svnsuperproject.SvnRepo") as mock_repo_cls:
        mock_repo_cls.return_value.externals.return_value = []
        with patch("os.getcwd", return_value="/some/dir"):
            result = SvnSuperProject.import_projects()

    assert result == []


def test_import_projects_maps_externals_to_project_entries():
    fake_external = Mock()
    fake_external.name = "mylib"
    fake_external.revision = "100"
    fake_external.url = "https://svn.example.com/mylib"
    fake_external.path = "libs/mylib"
    fake_external.branch = "trunk"
    fake_external.tag = ""
    fake_external.src = ""

    with patch("dfetch.project.svnsuperproject.SvnRepo") as mock_repo_cls:
        mock_repo_cls.return_value.externals.return_value = [fake_external]
        with patch("os.getcwd", return_value="/some/dir"):
            result = SvnSuperProject.import_projects()

    assert len(result) == 1
    assert result[0].name == "mylib"
    assert result[0].remote_url == "https://svn.example.com/mylib"
