"""Test dfetch.vcs.git_gitlinks."""

# mypy: ignore-errors
# flake8: noqa

import subprocess

import pytest

from dfetch.util.cmdline import SubprocessCommandError
from dfetch.vcs import git_gitlinks


def _init_git_repo(path):
    """Initialize a real git repo at *path* with a committer identity set.

    Args:
        path: Directory to initialize as a git repo.
    """
    subprocess.check_call(["git", "init", "--quiet"], cwd=path)
    subprocess.check_call(["git", "config", "user.email", "you@example.com"], cwd=path)
    subprocess.check_call(["git", "config", "user.name", "John Doe"], cwd=path)
    subprocess.check_call(["git", "config", "commit.gpgsign", "false"], cwd=path)


def _add_gitlink(path, gitlink_path):
    """Stage a gitlink (mode 160000) at *gitlink_path* using the repo's own HEAD sha."""
    sha = (
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path).decode().strip()
    )
    subprocess.check_call(
        [
            "git",
            "update-index",
            "--add",
            "--cacheinfo",
            f"160000,{sha},{gitlink_path}",
        ],
        cwd=path,
    )


def test_declared_submodule_paths_requires_a_url(tmp_path, monkeypatch):
    """A .gitmodules stanza with a path but no url must not count as declared.

    git submodule update --init --recursive fails on such a stanza with the
    same "No url found for submodule path" error as a fully undeclared
    gitlink, so it must be treated the same way: as an orphan to drop.
    """
    _init_git_repo(tmp_path)
    (tmp_path / "root").write_text("root")
    subprocess.check_call(["git", "add", "root"], cwd=tmp_path)
    subprocess.check_call(["git", "commit", "-qm", "initial"], cwd=tmp_path)
    _add_gitlink(tmp_path, "orphan")
    (tmp_path / ".gitmodules").write_text('[submodule "orphan"]\n\tpath = orphan\n')
    subprocess.check_call(["git", "add", ".gitmodules"], cwd=tmp_path)
    subprocess.check_call(
        ["git", "commit", "-qm", "path-only declaration"], cwd=tmp_path
    )

    monkeypatch.chdir(tmp_path)
    assert git_gitlinks.declared_submodule_paths() == set()


def test_declared_submodule_paths_propagates_malformed_gitmodules(
    tmp_path, monkeypatch
):
    """A malformed .gitmodules must raise, not be silently treated as 'no submodules'.

    Swallowing every SubprocessCommandError here would make
    drop_orphan_gitlinks() strip every gitlink -- including legitimately
    declared ones -- whenever .gitmodules simply fails to parse.
    """
    _init_git_repo(tmp_path)
    (tmp_path / ".gitmodules").write_text('[submodule "broken"\n')

    monkeypatch.chdir(tmp_path)
    with pytest.raises(SubprocessCommandError):
        git_gitlinks.declared_submodule_paths()


def test_drop_orphan_gitlinks_handles_leading_dash_path(tmp_path, monkeypatch):
    """A gitlink path starting with '-' must not be parsed as a git option.

    Without a '--' terminator before the path, `git update-index
    --force-remove --cacheinfo` would try to parse '--cacheinfo' as an
    option instead of a path and fail.
    """
    _init_git_repo(tmp_path)
    (tmp_path / "root").write_text("root")
    subprocess.check_call(["git", "add", "root"], cwd=tmp_path)
    subprocess.check_call(["git", "commit", "-qm", "initial"], cwd=tmp_path)
    _add_gitlink(tmp_path, "--cacheinfo")

    monkeypatch.chdir(tmp_path)
    git_gitlinks.drop_orphan_gitlinks()

    remaining = subprocess.check_output(
        ["git", "ls-files", "-s"], cwd=tmp_path
    ).decode()
    assert "--cacheinfo" not in remaining
