"""Tests for the ``dfetch add`` command."""

# mypy: ignore-errors
# flake8: noqa

import argparse
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from dfetch.commands.add import Add
from dfetch.manifest.manifest import Manifest
from dfetch.manifest.project import ProjectEntry, ProjectEntryDict
from dfetch.manifest.remote import Remote
from tests.manifest_mock import mock_manifest

# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _make_project(name: str, destination: str = "") -> Mock:
    p = Mock(spec=ProjectEntry)
    p.name = name
    p.destination = destination or name
    return p


def _make_remote(name: str, url: str) -> Mock:
    r = Mock(spec=Remote)
    r.name = name
    r.url = url
    return r


def _make_args(
    remote_url: str,
    interactive: bool = False,
) -> argparse.Namespace:
    return argparse.Namespace(
        remote_url=[remote_url],
        interactive=interactive,
    )


def _make_subproject(
    default_branch: str = "main",
    branches: list[str] | None = None,
    tags: list[str] | None = None,
) -> Mock:
    """Return a Mock SubProject with sensible defaults."""
    sp = Mock()
    sp.get_default_branch.return_value = default_branch
    sp.list_of_branches.return_value = (
        branches if branches is not None else [default_branch]
    )
    sp.list_of_tags.return_value = tags if tags is not None else []
    # browse_tree returns an empty ls_fn by default (no remote tree available)
    sp.browse_tree.return_value.__enter__ = Mock(return_value=lambda path="": [])
    sp.browse_tree.return_value.__exit__ = Mock(return_value=False)
    return sp


# ---------------------------------------------------------------------------
# Manifest.check_name_uniqueness
# ---------------------------------------------------------------------------


def test_check_name_uniqueness_raises_when_duplicate():
    m = Mock()
    m.projects = [_make_project("foo"), _make_project("bar")]
    with pytest.raises(ValueError, match="already exists"):
        Manifest.check_name_uniqueness(m, "foo")


def test_check_name_uniqueness_passes_for_new_name():
    m = Mock()
    m.projects = [_make_project("foo")]
    Manifest.check_name_uniqueness(m, "bar")  # should not raise


def test_check_name_uniqueness_passes_for_empty_manifest():
    m = Mock()
    m.projects = []
    Manifest.check_name_uniqueness(m, "anything")


# ---------------------------------------------------------------------------
# Manifest.guess_destination
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "project_name, existing, expected",
    [
        # No existing projects → empty string
        ("new", [], ""),
        # Single existing project in a subdirectory → use parent dir
        ("new", [("ext/a", "ext/a")], "ext/new"),
        # Two projects under ext/ → ext/new
        ("new", [("ext/a", "ext/a"), ("ext/b", "ext/b")], "ext/new"),
        # Projects with no common prefix → empty string
        ("new", [("a/x", "a/x"), ("b/y", "b/y")], ""),
    ],
)
def test_guess_destination(project_name, existing, expected):
    m = Mock()
    m.projects = [_make_project(name, dst) for name, dst in existing]
    assert Manifest.guess_destination(m, project_name) == expected


# ---------------------------------------------------------------------------
# Manifest.find_remote_for_url
# ---------------------------------------------------------------------------


def test_determine_remote_returns_matching_remote():
    m = Mock()
    m.remotes = [
        _make_remote("github", "https://github.com/"),
        _make_remote("gitlab", "https://gitlab.com/"),
    ]
    result = Manifest.find_remote_for_url(m, "https://github.com/myorg/myrepo.git")
    assert result is not None
    assert result.name == "github"


def test_determine_remote_returns_none_when_no_match():
    m = Mock()
    m.remotes = [_make_remote("github", "https://github.com/")]
    result = Manifest.find_remote_for_url(m, "https://bitbucket.org/myorg/myrepo.git")
    assert result is None


def test_determine_remote_returns_none_for_empty_remotes():
    m = Mock()
    m.remotes = []
    result = Manifest.find_remote_for_url(m, "https://github.com/myorg/myrepo.git")
    assert result is None


# ---------------------------------------------------------------------------
# Add command – non-interactive
# ---------------------------------------------------------------------------


def test_add_command_non_interactive_appends_entry():
    """Non-interactive add appends the entry to the manifest without any prompts."""
    fake_superproject = Mock()
    fake_superproject.manifest = mock_manifest(
        [{"name": "ext/existing"}], path="/some/dfetch.yaml"
    )
    fake_superproject.manifest.remotes = []
    fake_superproject.root_directory = Path("/some")

    fake_subproject = _make_subproject("main", ["main"], ["v1.0"])

    with patch(
        "dfetch.commands.add.create_super_project", return_value=fake_superproject
    ):
        with patch(
            "dfetch.commands.add.create_sub_project", return_value=fake_subproject
        ):
            with patch("dfetch.commands.add.append_entry_manifest_file") as mock_append:
                Add()(_make_args("https://github.com/org/myrepo.git"))

    mock_append.assert_called_once()
    entry: ProjectEntry = mock_append.call_args[0][1]
    assert entry.name == "myrepo"
    assert entry.branch == "main"


def test_add_command_suffixes_duplicate_name(tmp_path):
    """Non-interactive add with a clashing name must append a numbered suffix."""
    manifest_file = tmp_path / "dfetch.yaml"
    manifest_file.write_text("")

    fake_superproject = Mock()
    fake_superproject.manifest = mock_manifest(
        [{"name": "myrepo"}], path=str(manifest_file)
    )
    fake_superproject.manifest.remotes = []
    fake_superproject.root_directory = tmp_path

    fake_subproject = _make_subproject()

    with patch(
        "dfetch.commands.add.create_super_project", return_value=fake_superproject
    ):
        with patch(
            "dfetch.commands.add.create_sub_project", return_value=fake_subproject
        ):
            Add()(_make_args("https://github.com/org/myrepo.git"))

    assert "myrepo-1" in manifest_file.read_text()


# ---------------------------------------------------------------------------
# Add command – interactive mode
# ---------------------------------------------------------------------------


def test_add_command_interactive_branch():
    """Interactive mode: typing a branch name appends entry with that branch."""
    fake_superproject = Mock()
    fake_superproject.manifest = mock_manifest([], path="/some/dfetch.yaml")
    fake_superproject.manifest.remotes = []
    fake_superproject.root_directory = Path("/some")

    fake_subproject = _make_subproject("main", ["main", "dev"], ["v1.0"])

    # Prompts: name, dst, version, src, ignore (text fallback, non-TTY)
    prompt_answers = iter(["myrepo", "libs/myrepo", "dev", "", ""])

    with patch(
        "dfetch.commands.add.create_super_project", return_value=fake_superproject
    ):
        with patch(
            "dfetch.commands.add.create_sub_project", return_value=fake_subproject
        ):
            with patch(
                "dfetch.commands.add.Prompt.ask",
                side_effect=lambda *a, **kw: next(prompt_answers),
            ):
                with patch(
                    "dfetch.commands.add.Confirm.ask", side_effect=[True, False]
                ):
                    with patch(
                        "dfetch.commands.add.append_entry_manifest_file"
                    ) as mock_append:
                        Add()(
                            _make_args(
                                "https://github.com/org/myrepo.git",
                                interactive=True,
                            )
                        )

    mock_append.assert_called_once()
    entry: ProjectEntry = mock_append.call_args[0][1]
    assert entry.name == "myrepo"
    assert entry.branch == "dev"
    assert entry.destination == "libs/myrepo"


def test_add_command_interactive_branch_by_number():
    """Interactive mode: picking a branch by number selects it correctly."""
    fake_superproject = Mock()
    fake_superproject.manifest = mock_manifest([], path="/some/dfetch.yaml")
    fake_superproject.manifest.remotes = []
    fake_superproject.root_directory = Path("/some")

    fake_subproject = _make_subproject("main", ["main", "dev"], [])

    # "2" selects the second option in the pick list (dev).
    prompt_answers = iter(["myrepo", "myrepo", "2", "", ""])

    with patch(
        "dfetch.commands.add.create_super_project", return_value=fake_superproject
    ):
        with patch(
            "dfetch.commands.add.create_sub_project", return_value=fake_subproject
        ):
            with patch(
                "dfetch.commands.add.Prompt.ask",
                side_effect=lambda *a, **kw: next(prompt_answers),
            ):
                with patch(
                    "dfetch.commands.add.Confirm.ask", side_effect=[True, False]
                ):
                    with patch(
                        "dfetch.commands.add.append_entry_manifest_file"
                    ) as mock_append:
                        Add()(
                            _make_args(
                                "https://github.com/org/myrepo.git",
                                interactive=True,
                            )
                        )

    entry: ProjectEntry = mock_append.call_args[0][1]
    assert entry.branch == "dev"


def test_add_command_interactive_tag():
    """Interactive mode: typing a tag name appends entry with tag set."""
    fake_superproject = Mock()
    fake_superproject.manifest = mock_manifest([], path="/some/dfetch.yaml")
    fake_superproject.manifest.remotes = []
    fake_superproject.root_directory = Path("/some")

    fake_subproject = _make_subproject("main", ["main"], ["v1.0", "v2.0"])

    # version prompt: type the tag name directly.
    prompt_answers = iter(["myrepo", "myrepo", "v2.0", "", ""])

    with patch(
        "dfetch.commands.add.create_super_project", return_value=fake_superproject
    ):
        with patch(
            "dfetch.commands.add.create_sub_project", return_value=fake_subproject
        ):
            with patch(
                "dfetch.commands.add.Prompt.ask",
                side_effect=lambda *a, **kw: next(prompt_answers),
            ):
                with patch(
                    "dfetch.commands.add.Confirm.ask", side_effect=[True, False]
                ):
                    with patch(
                        "dfetch.commands.add.append_entry_manifest_file"
                    ) as mock_append:
                        Add()(
                            _make_args(
                                "https://github.com/org/myrepo.git",
                                interactive=True,
                            )
                        )

    mock_append.assert_called_once()
    entry: ProjectEntry = mock_append.call_args[0][1]
    assert entry.tag == "v2.0"
    assert entry.branch == ""


def test_add_command_interactive_abort():
    """Interactive mode: declining confirmation does not append."""
    fake_superproject = Mock()
    fake_superproject.manifest = mock_manifest([], path="/some/dfetch.yaml")
    fake_superproject.manifest.remotes = []
    fake_superproject.root_directory = Path("/some")

    fake_subproject = _make_subproject()

    prompt_answers = iter(["myrepo", "myrepo", "main", "", ""])

    with patch(
        "dfetch.commands.add.create_super_project", return_value=fake_superproject
    ):
        with patch(
            "dfetch.commands.add.create_sub_project", return_value=fake_subproject
        ):
            with patch(
                "dfetch.commands.add.Prompt.ask",
                side_effect=lambda *a, **kw: next(prompt_answers),
            ):
                with patch("dfetch.commands.add.Confirm.ask", return_value=False):
                    with patch(
                        "dfetch.commands.add.append_entry_manifest_file"
                    ) as mock_append:
                        Add()(
                            _make_args(
                                "https://github.com/org/myrepo.git",
                                interactive=True,
                            )
                        )

    mock_append.assert_not_called()


def test_add_command_interactive_with_src():
    """Interactive mode: providing a src path includes it in the entry."""
    fake_superproject = Mock()
    fake_superproject.manifest = mock_manifest([], path="/some/dfetch.yaml")
    fake_superproject.manifest.remotes = []
    fake_superproject.root_directory = Path("/some")

    fake_subproject = _make_subproject()

    # Prompts: name, dst, version, src, ignore
    answers = iter(["myrepo", "myrepo", "main", "include/", ""])

    with patch(
        "dfetch.commands.add.create_super_project", return_value=fake_superproject
    ):
        with patch(
            "dfetch.commands.add.create_sub_project", return_value=fake_subproject
        ):
            with patch(
                "dfetch.commands.add.Prompt.ask",
                side_effect=lambda *a, **kw: next(answers),
            ):
                with patch(
                    "dfetch.commands.add.Confirm.ask", side_effect=[True, False]
                ):
                    with patch(
                        "dfetch.commands.add.append_entry_manifest_file"
                    ) as mock_append:
                        Add()(
                            _make_args(
                                "https://github.com/org/myrepo.git",
                                interactive=True,
                            )
                        )

    mock_append.assert_called_once()
    entry: ProjectEntry = mock_append.call_args[0][1]
    assert entry.source == "include/"


def test_add_command_interactive_with_ignore():
    """Interactive mode: providing ignore paths includes them in the entry."""
    fake_superproject = Mock()
    fake_superproject.manifest = mock_manifest([], path="/some/dfetch.yaml")
    fake_superproject.manifest.remotes = []
    fake_superproject.root_directory = Path("/some")

    fake_subproject = _make_subproject()

    # Prompts: name, dst, version, src (empty), ignore (comma-separated)
    answers = iter(["myrepo", "myrepo", "main", "", "tests, docs"])

    with patch(
        "dfetch.commands.add.create_super_project", return_value=fake_superproject
    ):
        with patch(
            "dfetch.commands.add.create_sub_project", return_value=fake_subproject
        ):
            with patch(
                "dfetch.commands.add.Prompt.ask",
                side_effect=lambda *a, **kw: next(answers),
            ):
                with patch(
                    "dfetch.commands.add.Confirm.ask", side_effect=[True, False]
                ):
                    with patch(
                        "dfetch.commands.add.append_entry_manifest_file"
                    ) as mock_append:
                        Add()(
                            _make_args(
                                "https://github.com/org/myrepo.git",
                                interactive=True,
                            )
                        )

    mock_append.assert_called_once()
    entry: ProjectEntry = mock_append.call_args[0][1]
    assert list(entry.ignore) == ["tests", "docs"]


def test_add_command_interactive_run_update():
    """Interactive mode: confirming update calls the Update command."""
    fake_superproject = Mock()
    fake_superproject.manifest = mock_manifest([], path="/some/dfetch.yaml")
    fake_superproject.manifest.remotes = []
    fake_superproject.root_directory = Path("/some")

    fake_subproject = _make_subproject()

    prompt_answers = iter(["myrepo", "myrepo", "main", "", ""])

    with patch(
        "dfetch.commands.add.create_super_project", return_value=fake_superproject
    ):
        with patch(
            "dfetch.commands.add.create_sub_project", return_value=fake_subproject
        ):
            with patch(
                "dfetch.commands.add.Prompt.ask",
                side_effect=lambda *a, **kw: next(prompt_answers),
            ):
                with patch("dfetch.commands.add.Confirm.ask", side_effect=[True, True]):
                    with patch("dfetch.commands.add.append_entry_manifest_file"):
                        with patch(
                            "dfetch.commands.update.Update.__call__"
                        ) as mock_update:
                            Add()(
                                _make_args(
                                    "https://github.com/org/myrepo.git",
                                    interactive=True,
                                )
                            )

    mock_update.assert_called_once()


# ---------------------------------------------------------------------------
# Add command – interactive mode (SVN)
# ---------------------------------------------------------------------------

_SVN_URL = "svn://example.com/myrepo"


def _make_svn_subproject(
    branches: list[str] | None = None,
    tags: list[str] | None = None,
) -> Mock:
    """Return a Mock SVN SubProject with ``trunk`` as default branch."""
    all_branches = branches if branches is not None else ["trunk"]
    return _make_subproject(
        default_branch="trunk",
        branches=all_branches,
        tags=tags if tags is not None else [],
    )


def test_add_command_interactive_svn_trunk():
    """SVN interactive add: accepting the default trunk branch."""
    fake_superproject = Mock()
    fake_superproject.manifest = mock_manifest([], path="/some/dfetch.yaml")
    fake_superproject.manifest.remotes = []
    fake_superproject.root_directory = Path("/some")

    fake_subproject = _make_svn_subproject()

    # Prompts: name, dst, version (trunk), src, ignore
    answers = iter(["myrepo", "myrepo", "trunk", "", ""])

    with patch(
        "dfetch.commands.add.create_super_project", return_value=fake_superproject
    ):
        with patch(
            "dfetch.commands.add.create_sub_project", return_value=fake_subproject
        ):
            with patch(
                "dfetch.commands.add.Prompt.ask",
                side_effect=lambda *a, **kw: next(answers),
            ):
                with patch(
                    "dfetch.commands.add.Confirm.ask", side_effect=[True, False]
                ):
                    with patch(
                        "dfetch.commands.add.append_entry_manifest_file"
                    ) as mock_append:
                        Add()(_make_args(_SVN_URL, interactive=True))

    mock_append.assert_called_once()
    entry: ProjectEntry = mock_append.call_args[0][1]
    assert entry.name == "myrepo"
    assert entry.branch == "trunk"


def test_add_command_interactive_svn_custom_branch():
    """SVN interactive add: selecting a branch from ``branches/``."""
    fake_superproject = Mock()
    fake_superproject.manifest = mock_manifest([], path="/some/dfetch.yaml")
    fake_superproject.manifest.remotes = []
    fake_superproject.root_directory = Path("/some")

    fake_subproject = _make_svn_subproject(branches=["trunk", "feature-x"])

    # Prompts: name, dst, version (feature-x), src, ignore
    answers = iter(["myrepo", "myrepo", "feature-x", "", ""])

    with patch(
        "dfetch.commands.add.create_super_project", return_value=fake_superproject
    ):
        with patch(
            "dfetch.commands.add.create_sub_project", return_value=fake_subproject
        ):
            with patch(
                "dfetch.commands.add.Prompt.ask",
                side_effect=lambda *a, **kw: next(answers),
            ):
                with patch(
                    "dfetch.commands.add.Confirm.ask", side_effect=[True, False]
                ):
                    with patch(
                        "dfetch.commands.add.append_entry_manifest_file"
                    ) as mock_append:
                        Add()(_make_args(_SVN_URL, interactive=True))

    entry: ProjectEntry = mock_append.call_args[0][1]
    assert entry.branch == "feature-x"


def test_add_command_interactive_svn_tag():
    """SVN interactive add: selecting a tag."""
    fake_superproject = Mock()
    fake_superproject.manifest = mock_manifest([], path="/some/dfetch.yaml")
    fake_superproject.manifest.remotes = []
    fake_superproject.root_directory = Path("/some")

    fake_subproject = _make_svn_subproject(tags=["v1.0", "v2.0"])

    # Prompts: name, dst, version (v2.0 by name), src, ignore
    answers = iter(["myrepo", "myrepo", "v2.0", "", ""])

    with patch(
        "dfetch.commands.add.create_super_project", return_value=fake_superproject
    ):
        with patch(
            "dfetch.commands.add.create_sub_project", return_value=fake_subproject
        ):
            with patch(
                "dfetch.commands.add.Prompt.ask",
                side_effect=lambda *a, **kw: next(answers),
            ):
                with patch(
                    "dfetch.commands.add.Confirm.ask", side_effect=[True, False]
                ):
                    with patch(
                        "dfetch.commands.add.append_entry_manifest_file"
                    ) as mock_append:
                        Add()(_make_args(_SVN_URL, interactive=True))

    entry: ProjectEntry = mock_append.call_args[0][1]
    assert entry.tag == "v2.0"
    assert entry.branch == ""


def test_add_command_interactive_svn_branch_by_number():
    """SVN interactive add: selecting a branch by its number in the pick list."""
    fake_superproject = Mock()
    fake_superproject.manifest = mock_manifest([], path="/some/dfetch.yaml")
    fake_superproject.manifest.remotes = []
    fake_superproject.root_directory = Path("/some")

    # choices order: trunk (default, index 1), feature-x (index 2)
    fake_subproject = _make_svn_subproject(branches=["trunk", "feature-x"])

    answers = iter(["myrepo", "myrepo", "2", "", ""])

    with patch(
        "dfetch.commands.add.create_super_project", return_value=fake_superproject
    ):
        with patch(
            "dfetch.commands.add.create_sub_project", return_value=fake_subproject
        ):
            with patch(
                "dfetch.commands.add.Prompt.ask",
                side_effect=lambda *a, **kw: next(answers),
            ):
                with patch(
                    "dfetch.commands.add.Confirm.ask", side_effect=[True, False]
                ):
                    with patch(
                        "dfetch.commands.add.append_entry_manifest_file"
                    ) as mock_append:
                        Add()(_make_args(_SVN_URL, interactive=True))

    entry: ProjectEntry = mock_append.call_args[0][1]
    assert entry.branch == "feature-x"


def test_add_command_non_interactive_svn():
    """SVN non-interactive add defaults to trunk."""
    fake_superproject = Mock()
    fake_superproject.manifest = mock_manifest([], path="/some/dfetch.yaml")
    fake_superproject.manifest.remotes = []
    fake_superproject.root_directory = Path("/some")

    fake_subproject = _make_svn_subproject()

    with patch(
        "dfetch.commands.add.create_super_project", return_value=fake_superproject
    ):
        with patch(
            "dfetch.commands.add.create_sub_project", return_value=fake_subproject
        ):
            with patch("dfetch.commands.add.append_entry_manifest_file") as mock_append:
                Add()(_make_args(_SVN_URL))

    mock_append.assert_called_once()
    entry: ProjectEntry = mock_append.call_args[0][1]
    assert entry.branch == "trunk"


# ---------------------------------------------------------------------------
# Add command – remote matching
# ---------------------------------------------------------------------------


def test_add_command_matches_existing_remote():
    """When the URL matches a known remote, the entry uses repo-path."""
    fake_remote = MagicMock()
    fake_remote.name = "github"
    fake_remote.url = "https://github.com/"

    fake_superproject = Mock()
    fake_superproject.manifest = mock_manifest([], path="/some/dfetch.yaml")
    fake_superproject.manifest.remotes = [fake_remote]
    fake_superproject.root_directory = Path("/some")

    fake_subproject = _make_subproject()

    with patch(
        "dfetch.commands.add.create_super_project", return_value=fake_superproject
    ):
        with patch(
            "dfetch.commands.add.create_sub_project", return_value=fake_subproject
        ):
            with patch("dfetch.commands.add.append_entry_manifest_file") as mock_append:
                Add()(
                    _make_args(
                        "https://github.com/org/myrepo.git",
                    )
                )

    mock_append.assert_called_once()
    entry: ProjectEntry = mock_append.call_args[0][1]
    yaml_data = entry.as_yaml()
    assert yaml_data.get("remote") == "github"
    assert "org/myrepo" in yaml_data.get("repo-path", "")
    assert "url" not in yaml_data


# ---------------------------------------------------------------------------
# CLI menu creation
# ---------------------------------------------------------------------------


def test_add_create_menu():
    import argparse

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    Add.create_menu(subparsers)
    parsed = parser.parse_args(["add", "https://example.com/repo.git"])
    assert parsed.remote_url == ["https://example.com/repo.git"]
    assert not hasattr(parsed, "force")


def test_add_create_menu_interactive_flag():
    import argparse

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    Add.create_menu(subparsers)
    parsed = parser.parse_args(["add", "-i", "https://example.com/repo.git"])
    assert parsed.interactive is True
