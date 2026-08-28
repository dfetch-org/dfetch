"""Test dfetch.vcs.git_submodule."""

# mypy: ignore-errors
# flake8: noqa

import subprocess
from unittest.mock import patch

import pytest

from dfetch.util.cmdline import SubprocessCommandError
from dfetch.vcs import git_submodule
from dfetch.vcs.git_submodule import Submodule

# ---------------------------------------------------------------------------
# move_src_folder_up — path-traversal guards
# ---------------------------------------------------------------------------


def test_move_src_folder_up_rejects_absolute_src(tmp_path):
    """An absolute src pattern must be rejected without touching the filesystem."""
    with patch("dfetch.vcs.git_submodule.move_directory_contents") as mock_move:
        with patch("dfetch.vcs.git_submodule.os.getcwd", return_value=str(tmp_path)):
            git_submodule.move_src_folder_up("my-remote", "/etc")
    mock_move.assert_not_called()


def test_move_src_folder_up_rejects_traversal_src(tmp_path):
    """A src pattern that resolves outside the repo root must be skipped."""
    outside = tmp_path.parent / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("data")

    with patch("dfetch.vcs.git_submodule.move_directory_contents") as mock_move:
        with patch("dfetch.util.util.glob.glob", return_value=[str(outside)]):
            with patch(
                "dfetch.vcs.git_submodule.os.getcwd", return_value=str(tmp_path)
            ):
                git_submodule.move_src_folder_up("my-remote", "../outside")
    mock_move.assert_not_called()


# ---------------------------------------------------------------------------
# filter_submodules_by_src
# ---------------------------------------------------------------------------


def _make_submodule(path: str, url: str = "some-url") -> Submodule:
    return Submodule(
        name=path,
        toplevel="",
        path=path,
        sha="abc123",
        url=url,
        branch="master",
        tag="",
    )


def test_filter_submodules_ancestor_of_src_not_removed(tmp_path, monkeypatch):
    """A submodule whose path is an ancestor of src must not be deleted.

    When src='apps/myapp' and a submodule exists at 'apps', the old logic
    incorrectly added 'apps' to to_remove (because Path('apps/myapp').is_relative_to('apps')
    was True with sub_top='apps').  The fix checks the full submodule.path so that an
    ancestor submodule is skipped and move_src_folder_up can promote its content.
    """
    (tmp_path / "apps" / "myapp").mkdir(parents=True)
    (tmp_path / "apps" / "myapp" / "README.md").write_text("content")
    (tmp_path / "outside").mkdir()
    (tmp_path / "outside" / "file.txt").write_text("content")

    monkeypatch.chdir(tmp_path)
    result = git_submodule.filter_submodules_by_src(
        "remote-url",
        "apps/myapp",
        [_make_submodule("apps"), _make_submodule("outside")],
    )

    assert (
        tmp_path / "README.md"
    ).exists(), "apps/myapp content should be promoted to root"
    assert not (tmp_path / "outside").exists(), "outside/ submodule should be removed"
    assert not any(
        s.path == "apps" for s in result
    ), "ancestor submodule must not appear in result"
    assert not any(
        s.path == "outside" for s in result
    ), "out-of-scope submodule must not appear in result"


def test_filter_submodules_disjoint_submodule_removed(tmp_path, monkeypatch):
    """A submodule whose path is disjoint from src must be removed.

    The fix stores the full submodule.path (not its top-level component) in
    to_remove, so only the exact submodule directory is deleted.
    """
    (tmp_path / "src_folder" / "ext" / "inside").mkdir(parents=True)
    (tmp_path / "src_folder" / "ext" / "inside" / "README.md").write_text("content")
    (tmp_path / "other_ext" / "outside").mkdir(parents=True)
    (tmp_path / "other_ext" / "outside" / "README.md").write_text("content")

    monkeypatch.chdir(tmp_path)
    result = git_submodule.filter_submodules_by_src(
        "remote-url",
        "src_folder",
        [
            _make_submodule("src_folder/ext/inside"),
            _make_submodule("other_ext/outside"),
        ],
    )

    assert not (
        tmp_path / "other_ext" / "outside"
    ).exists(), "other_ext/outside submodule dir should be removed"
    assert any(
        s.path == "ext/inside" for s in result
    ), "inside submodule should be promoted"


def test_filter_submodules_sibling_of_src_not_removed(tmp_path, monkeypatch):
    """A sibling submodule sharing the same top-level dir as src must not destroy src content.

    When src='apps/lib' and submodules exist at both 'apps/lib' (exact match, the src)
    and 'apps/widget' (sibling, outside src), the old logic used parts[0]='apps' and
    called safe_rm('apps'), which deleted the entire apps/ directory — including the
    already-cloned apps/lib content needed by move_src_folder_up.
    The fix stores the full submodule.path so only apps/widget is targeted, leaving
    apps/lib intact for promotion.
    """
    (tmp_path / "apps" / "lib").mkdir(parents=True)
    (tmp_path / "apps" / "lib" / "README.md").write_text("content")
    (tmp_path / "apps" / "widget").mkdir(parents=True)
    (tmp_path / "apps" / "widget" / "widget.h").write_text("content")

    monkeypatch.chdir(tmp_path)
    result = git_submodule.filter_submodules_by_src(
        "remote-url",
        "apps/lib",
        [_make_submodule("apps/lib"), _make_submodule("apps/widget")],
    )

    assert (
        tmp_path / "README.md"
    ).exists(), "apps/lib content must be promoted to root"
    assert not (
        tmp_path / "apps" / "widget"
    ).exists(), "sibling apps/widget must be removed"
    assert any(
        s.path == "apps/lib" for s in result
    ), "src submodule should appear in result before final os.path.exists filtering"


# ---------------------------------------------------------------------------
# Orphan gitlinks -- gitlinks with no matching .gitmodules entry (#1380)
# ---------------------------------------------------------------------------


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
    assert git_submodule.declared_submodule_paths() == set()


def test_declared_submodule_paths_propagates_malformed_gitmodules(
    tmp_path, monkeypatch
):
    """A malformed .gitmodules must raise, not be silently treated as 'no submodules'.

    Swallowing every SubprocessCommandError here would make
    orphan_gitlinks_dropped() strip every gitlink -- including legitimately
    declared ones -- whenever .gitmodules simply fails to parse.
    """
    _init_git_repo(tmp_path)
    (tmp_path / ".gitmodules").write_text('[submodule "broken"\n')

    monkeypatch.chdir(tmp_path)
    with pytest.raises(SubprocessCommandError):
        git_submodule.declared_submodule_paths()


def test_orphan_gitlinks_dropped_handles_leading_dash_path(tmp_path, monkeypatch):
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
    with git_submodule.orphan_gitlinks_dropped():
        remaining = subprocess.check_output(
            ["git", "ls-files", "-s"], cwd=tmp_path
        ).decode()
        assert "--cacheinfo" not in remaining


def test_orphan_gitlinks_dropped_restores_the_index_on_exit(tmp_path, monkeypatch):
    """Stripped gitlinks must be re-staged once the context manager exits.

    orphan_gitlinks_dropped() can run against a repository dfetch does not
    own (e.g. the user's own working directory during `dfetch import`), so
    it must not leave a lasting change there.
    """
    _init_git_repo(tmp_path)
    (tmp_path / "root").write_text("root")
    subprocess.check_call(["git", "add", "root"], cwd=tmp_path)
    subprocess.check_call(["git", "commit", "-qm", "initial"], cwd=tmp_path)
    _add_gitlink(tmp_path, "orphan")
    subprocess.check_call(["git", "commit", "-qm", "add orphan gitlink"], cwd=tmp_path)

    monkeypatch.chdir(tmp_path)
    index_before = subprocess.check_output(
        ["git", "ls-files", "-s"], cwd=tmp_path
    ).decode()
    # The gitlink was committed with no real submodule checked out under it, so
    # git already reports it deleted-in-worktree before any dropping happens;
    # the point here is that this baseline noise is unchanged by the fix.
    status_before = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=tmp_path
    ).decode()

    with git_submodule.orphan_gitlinks_dropped():
        during = subprocess.check_output(
            ["git", "ls-files", "-s"], cwd=tmp_path
        ).decode()
        assert "orphan" not in during

    index_after = subprocess.check_output(
        ["git", "ls-files", "-s"], cwd=tmp_path
    ).decode()
    status_after = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=tmp_path
    ).decode()
    assert index_after == index_before
    assert status_after == status_before


def test_orphan_gitlinks_dropped_restores_even_when_body_raises(tmp_path, monkeypatch):
    """The index must be restored even if the wrapped git command fails.

    checkout_version() wraps a real `git submodule update --init --recursive`
    call that can itself fail (e.g. an unrelated bad URL, or the nested-orphan
    case). Restoration relies on try/finally rather than a plain sequential
    drop-then-restore, so this locks that in: a failure inside the `with`
    block must not leave an orphan gitlink stripped from the index, and the
    original exception must still propagate rather than being swallowed.
    """
    _init_git_repo(tmp_path)
    (tmp_path / "root").write_text("root")
    subprocess.check_call(["git", "add", "root"], cwd=tmp_path)
    subprocess.check_call(["git", "commit", "-qm", "initial"], cwd=tmp_path)
    _add_gitlink(tmp_path, "orphan")
    subprocess.check_call(["git", "commit", "-qm", "add orphan gitlink"], cwd=tmp_path)

    monkeypatch.chdir(tmp_path)
    index_before = subprocess.check_output(
        ["git", "ls-files", "-s"], cwd=tmp_path
    ).decode()

    class _Boom(Exception):
        pass

    with pytest.raises(_Boom):
        with git_submodule.orphan_gitlinks_dropped():
            during = subprocess.check_output(
                ["git", "ls-files", "-s"], cwd=tmp_path
            ).decode()
            assert "orphan" not in during
            raise _Boom("simulated failure of the wrapped git submodule command")

    index_after = subprocess.check_output(
        ["git", "ls-files", "-s"], cwd=tmp_path
    ).decode()
    assert index_after == index_before


def test_orphan_gitlinks_dropped_leaves_a_conflicted_gitlink_untouched(
    tmp_path, monkeypatch
):
    """An unresolved merge conflict on an orphan gitlink must not be collapsed.

    A conflicted path occupies multiple non-zero index "stages" instead of
    the usual stage 0. Restoring via `update-index --cacheinfo` always
    writes stage 0, so round-tripping a conflicted gitlink through drop and
    restore would silently discard one side of the conflict and mark it
    resolved -- corrupting a repository dfetch does not own (e.g. mid-merge
    during `dfetch import`). Such a path must be left out of dropping
    entirely.
    """
    _init_git_repo(tmp_path)
    (tmp_path / "root").write_text("root")
    subprocess.check_call(["git", "add", "root"], cwd=tmp_path)
    subprocess.check_call(["git", "commit", "-qm", "base"], cwd=tmp_path)
    base_branch = (
        subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=tmp_path
        )
        .decode()
        .strip()
    )

    subprocess.check_call(["git", "checkout", "-qb", "branch-a"], cwd=tmp_path)
    _add_gitlink(tmp_path, "stray")
    subprocess.check_call(["git", "commit", "-qm", "branch-a stray"], cwd=tmp_path)

    subprocess.check_call(["git", "checkout", "-q", base_branch], cwd=tmp_path)
    subprocess.check_call(["git", "checkout", "-qb", "branch-b"], cwd=tmp_path)
    (tmp_path / "root").write_text("root\nmore\n")
    subprocess.check_call(["git", "add", "root"], cwd=tmp_path)
    subprocess.check_call(["git", "commit", "-qm", "branch-b change"], cwd=tmp_path)
    _add_gitlink(tmp_path, "stray")  # same path, different sha -> a real conflict
    subprocess.check_call(["git", "commit", "-qm", "branch-b stray"], cwd=tmp_path)

    subprocess.run(["git", "merge", "branch-a"], cwd=tmp_path, check=False)

    monkeypatch.chdir(tmp_path)
    index_before = subprocess.check_output(
        ["git", "ls-files", "-s"], cwd=tmp_path
    ).decode()
    stray_stages = [line for line in index_before.splitlines() if "stray" in line]
    assert len(stray_stages) == 2, "expected two conflicted stages for 'stray'"

    with git_submodule.orphan_gitlinks_dropped():
        during = subprocess.check_output(
            ["git", "ls-files", "-s"], cwd=tmp_path
        ).decode()
        assert during == index_before

    index_after = subprocess.check_output(
        ["git", "ls-files", "-s"], cwd=tmp_path
    ).decode()
    status_after = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=tmp_path
    ).decode()
    assert index_after == index_before
    assert status_after.strip() == "AA stray"
