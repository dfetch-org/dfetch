"""Tests for dfetch.project.gitsuperproject.GitSuperProject."""

# mypy: ignore-errors
# flake8: noqa

import pathlib
from unittest.mock import MagicMock, Mock, patch

import pytest

from dfetch.manifest.manifest import Manifest
from dfetch.manifest.project import ProjectEntry
from dfetch.project.gitsuperproject import GitSuperProject
from dfetch.project.superproject import RevisionRange


def _make_superproject(root: str = "/some/root") -> GitSuperProject:
    """Build a GitSuperProject with a mocked GitLocalRepo."""
    manifest = MagicMock(spec=Manifest)
    manifest.path = f"{root}/dfetch.yaml"
    with patch("dfetch.project.gitsuperproject.GitLocalRepo"):
        return GitSuperProject(manifest, pathlib.Path(root))


def test_check_returns_true_when_git_repo():
    with patch("dfetch.project.gitsuperproject.GitLocalRepo") as mock_repo_cls:
        mock_repo_cls.return_value.is_git.return_value = True
        assert GitSuperProject.check("/some/path") is True


def test_check_returns_false_when_not_git_repo():
    with patch("dfetch.project.gitsuperproject.GitLocalRepo") as mock_repo_cls:
        mock_repo_cls.return_value.is_git.return_value = False
        assert GitSuperProject.check("/some/path") is False


def test_get_sub_project_returns_git_sub_project():
    superproject = _make_superproject()
    project = ProjectEntry({"name": "mylib", "url": "https://example.com/mylib"})

    with patch("dfetch.project.gitsuperproject.GitSubProject") as mock_cls:
        result = superproject.get_sub_project(project)
        mock_cls.assert_called_once_with(project)
        assert result == mock_cls.return_value


def test_ignored_files_delegates_to_git_local_repo():
    superproject = _make_superproject(root="/repo")

    with patch("dfetch.project.gitsuperproject.GitLocalRepo") as mock_repo_cls:
        mock_repo_cls.return_value.ignored_files.return_value = ["a.pyc"]
        with patch(
            "dfetch.project.gitsuperproject.resolve_absolute_path",
            return_value=pathlib.Path("/repo/vendor"),
        ):
            with patch("dfetch.project.gitsuperproject.check_no_path_traversal"):
                result = superproject.ignored_files("vendor")

        assert result == ["a.pyc"]


def test_has_local_changes_in_dir_returns_true_when_changed():
    superproject = _make_superproject()

    with patch("dfetch.project.gitsuperproject.GitLocalRepo") as mock_repo_cls:
        mock_repo_cls.return_value.any_changes_or_untracked.return_value = True
        result = superproject.has_local_changes_in_dir("some/path")

    assert result is True


def test_has_local_changes_in_dir_returns_false_when_clean():
    superproject = _make_superproject()

    with patch("dfetch.project.gitsuperproject.GitLocalRepo") as mock_repo_cls:
        mock_repo_cls.return_value.any_changes_or_untracked.return_value = False
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


def test_get_useremail_returns_repo_email_when_set():
    superproject = _make_superproject()

    with patch.object(superproject, "_repo") as mock_repo:
        mock_repo.get_useremail.return_value = "alice@example.com"
        assert superproject.get_useremail() == "alice@example.com"


def test_get_useremail_falls_back_when_repo_returns_empty():
    superproject = _make_superproject()

    with patch.object(superproject, "_repo") as mock_repo:
        mock_repo.get_useremail.return_value = ""
        with patch.object(superproject, "get_username", return_value="bob"):
            result = superproject.get_useremail()
    assert result == "bob@example.com"


def test_get_file_revision_returns_hash():
    superproject = _make_superproject()

    with patch.object(superproject, "_repo") as mock_repo:
        mock_repo.get_last_file_hash.return_value = "deadbeef"
        result = superproject.get_file_revision("some/file.txt")

    assert result == "deadbeef"


def test_eol_preferences_delegates_to_repo():
    superproject = _make_superproject()

    with patch.object(superproject, "_repo") as mock_repo:
        mock_repo.eol_attributes.return_value = {"a.txt": "lf"}
        result = superproject.eol_preferences(["a.txt"])

    assert result == {"a.txt": "lf"}


def test_diff_with_new_revision_returns_diff_directly():
    superproject = _make_superproject()

    with patch("dfetch.project.gitsuperproject.GitLocalRepo") as mock_repo_cls:
        mock_repo_cls.return_value.create_diff.return_value = "some diff"
        result = superproject.diff(
            "some/path",
            revisions=RevisionRange(old="abc", new="def"),
            ignore=(),
        )

    assert result == "some diff"


def test_diff_without_new_revision_includes_untracked():
    superproject = _make_superproject()

    fake_patch = Mock()
    fake_patch.is_empty.return_value = False
    fake_patch.dump.return_value = "untracked patch"

    with patch("dfetch.project.gitsuperproject.GitLocalRepo") as mock_repo_cls:
        mock_repo_cls.return_value.create_diff.return_value = "committed diff"
        mock_repo_cls.return_value.untracked_files_patch.return_value = fake_patch
        result = superproject.diff(
            "some/path",
            revisions=RevisionRange(old="abc", new=""),
            ignore=(),
        )

    assert "committed diff" in result
    assert "untracked patch" in result


def test_diff_without_new_revision_empty_untracked_not_included():
    superproject = _make_superproject()

    fake_patch = Mock()
    fake_patch.is_empty.return_value = True

    with patch("dfetch.project.gitsuperproject.GitLocalRepo") as mock_repo_cls:
        mock_repo_cls.return_value.create_diff.return_value = "committed diff"
        mock_repo_cls.return_value.untracked_files_patch.return_value = fake_patch
        result = superproject.diff(
            "some/path",
            revisions=RevisionRange(old="abc", new=""),
            ignore=(),
        )

    assert result == "committed diff"


def test_import_projects_returns_empty_when_no_submodules():
    with patch("dfetch.project.gitsuperproject.GitLocalRepo") as mock_cls:
        mock_cls.submodules.return_value = []
        with patch("os.getcwd", return_value="/some/dir"):
            result = GitSuperProject.import_projects()

    assert result == []


def test_import_projects_returns_projects_from_submodules():
    fake_submodule = Mock()
    fake_submodule.name = "mylib"
    fake_submodule.sha = "deadbeef"
    fake_submodule.url = "https://example.com/mylib"
    fake_submodule.path = "libs/mylib"
    fake_submodule.branch = "main"
    fake_submodule.tag = ""
    fake_submodule.toplevel = "/some/dir"

    with patch("dfetch.project.gitsuperproject.GitLocalRepo") as mock_cls:
        mock_cls.submodules.return_value = [fake_submodule]
        with patch("os.getcwd", return_value="/some/dir"):
            with patch("os.path.realpath", return_value="/some/dir"):
                result = GitSuperProject.import_projects()

    assert len(result) == 1
    assert result[0].name == "mylib"
