"""Unit tests for the dfetch filter command."""

# mypy: ignore-errors

import argparse
import io

import pytest

from dfetch.commands.filter import (
    _filter_candidates,
    _gather_candidates,
    _is_dfetched,
    _walk_paths,
)


@pytest.fixture(name="project_tree")
def fixture_project_tree(tmp_path, monkeypatch):
    """Create a small superproject with one vendored project directory."""
    root = tmp_path / "superproject"
    vendored = root / "third-party" / "mod"
    vendored.mkdir(parents=True)
    (vendored / "a.py").write_text("# vendored")
    (root / "own.py").write_text("# own")
    (root / "dfetch.yaml").write_text("manifest:")
    git_dir = root / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("")
    (tmp_path / "outside.txt").write_text("outside")

    monkeypatch.chdir(root)
    return root, {vendored}


def test_keeps_only_dfetched_paths(project_tree):
    """Paths inside a project destination are kept, others dropped."""
    root, project_dirs = project_tree

    kept = _filter_candidates(
        ["own.py", "third-party/mod/a.py"], root, project_dirs, keep_dfetched=True
    )

    assert kept == ["third-party/mod/a.py"]


def test_keeps_only_non_dfetched_paths(project_tree):
    """With the selection inverted only paths outside project destinations remain."""
    root, project_dirs = project_tree

    kept = _filter_candidates(
        ["own.py", "third-party/mod/a.py"], root, project_dirs, keep_dfetched=False
    )

    assert kept == ["own.py"]


def test_non_existing_paths_are_passed_through(project_tree):
    """Options for a wrapped tool aren't paths and must survive filtering."""
    root, project_dirs = project_tree

    kept = _filter_candidates(
        ["--check", "no-such-file.py"], root, project_dirs, keep_dfetched=True
    )

    assert kept == ["--check", "no-such-file.py"]


def test_paths_outside_root_are_dropped(project_tree):
    """Existing paths outside the manifest directory are always dropped."""
    root, project_dirs = project_tree

    for keep_dfetched in (True, False):
        kept = _filter_candidates(
            ["../outside.txt"], root, project_dirs, keep_dfetched=keep_dfetched
        )

        assert kept == []


def test_is_dfetched(project_tree):
    """A path is dfetched when it is below any project destination."""
    root, project_dirs = project_tree

    assert _is_dfetched(root / "third-party" / "mod" / "a.py", project_dirs)
    assert not _is_dfetched(root / "own.py", project_dirs)


def test_walk_lists_only_project_destinations(project_tree):
    """The dfetched listing walks the project destinations only."""
    root, project_dirs = project_tree

    paths = list(_walk_paths(root, project_dirs, keep_dfetched=True))

    assert paths == [
        root / "third-party" / "mod",
        root / "third-party" / "mod" / "a.py",
    ]


def test_walk_prunes_project_destinations_and_git(project_tree):
    """The non-dfetched listing skips project destinations and .git directories."""
    root, project_dirs = project_tree

    paths = set(_walk_paths(root, project_dirs, keep_dfetched=False))

    assert paths == {
        root / "dfetch.yaml",
        root / "own.py",
        root / "third-party",
    }


def test_gather_candidates_reads_args_and_stdin(monkeypatch):
    """Arguments and piped input are combined, empty lines skipped."""
    monkeypatch.setattr("sys.stdin", io.StringIO("piped.py\n\n  spaced.py  \n"))

    candidates = _gather_candidates(argparse.Namespace(args=["arg.py"]))

    assert candidates == ["arg.py", "piped.py", "spaced.py"]


def test_gather_candidates_skips_interactive_stdin(monkeypatch):
    """An interactive terminal is not read to avoid blocking on input."""

    class InteractiveStdin(io.StringIO):
        def isatty(self):
            return True

    monkeypatch.setattr("sys.stdin", InteractiveStdin("should not be read"))

    assert _gather_candidates(argparse.Namespace(args=[])) == []
