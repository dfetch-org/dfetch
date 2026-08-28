"""Everything dfetch needs for Git submodule handling, in one place.

Bundles the ``Submodule`` data type, detecting and neutralizing gitlinks
that have no matching ``.gitmodules`` entry (see #1380), resolving
submodule URLs/branches, and filtering/promoting a fetched submodule tree
according to a project's ``src``/``ignore`` settings.
"""

import contextlib
import glob
import os
import re
from collections.abc import Generator, Sequence
from dataclasses import dataclass
from pathlib import Path

from dfetch.log import get_logger
from dfetch.util.cmdline import SubprocessCommandError, run_on_cmdline
from dfetch.util.license import is_license_file
from dfetch.util.util import (
    glob_within_root,
    move_directory_contents,
    safe_rm,
    strip_glob_prefix,
    unique_parent_dirs,
)

METADATA_DIR = ".git"
GIT_MODULES_FILE = ".gitmodules"

logger = get_logger(__name__)


@dataclass
class Submodule:
    """Information about a submodule."""

    name: str
    toplevel: str
    path: str
    sha: str
    url: str
    branch: str
    tag: str


# ---------------------------------------------------------------------------
# Orphan gitlinks -- gitlinks with no matching .gitmodules entry (#1380)
#
# Some repositories contain gitlinks (mode ``160000``) that have no matching
# entry in ``.gitmodules`` -- for example an accidentally committed
# ``git worktree`` directory or nested checkout. Both ``git submodule update
# --init --recursive`` and ``git submodule foreach`` abort outright as soon
# as they encounter such a gitlink, even though dfetch has no URL to fetch
# it from and nothing useful to report about it anyway.
# ---------------------------------------------------------------------------


def _gitlink_entries() -> list[tuple[str, str]]:
    """List (path, sha) for every gitlink (mode 160000) in the current index."""
    result = run_on_cmdline(logger, ["git", "ls-files", "-s", "-z"])
    entries = []
    for entry in result.stdout.decode().split("\0"):
        if not entry:
            continue
        meta, _, path = entry.partition("\t")
        mode, sha = meta.split()[:2]
        if mode == "160000":
            entries.append((path, sha))
    return entries


def _submodule_config_values(key: str) -> dict[str, str]:
    """Return {submodule name: value} for a .gitmodules key ("path" or "url").

    Args:
        key: The per-submodule config key to read, e.g. "path" or "url".
    """
    try:
        result = run_on_cmdline(
            logger,
            ["git", "config", "--file", GIT_MODULES_FILE, "--get-regexp", key],
        )
    except SubprocessCommandError as exc:
        # get-regexp documents exit status 1 for "no matching lines"; anything
        # else (e.g. a malformed .gitmodules) must not be mistaken for that.
        if exc.returncode == 1:
            return {}
        raise
    return {
        match.group(1): match.group(2)
        for match in re.finditer(
            rf"submodule\.(.*)\.{key}\s+(.*)", result.stdout.decode()
        )
    }


def declared_submodule_paths() -> set[str]:
    """Return the paths of .gitmodules submodules that also declare a url.

    A stanza with a ``path`` but no ``url`` cannot be initialized by
    ``git submodule update`` either, so it is treated the same as an orphan
    gitlink rather than as "declared".
    """
    if not os.path.isfile(GIT_MODULES_FILE):
        return set()
    paths = _submodule_config_values("path")
    urls = _submodule_config_values("url")
    return {path for name, path in paths.items() if name in urls}


@contextlib.contextmanager
def orphan_gitlinks_dropped() -> Generator[None, None, None]:
    """Temporarily strip gitlinks with no .gitmodules entry from the index.

    Such a gitlink has no declared URL, so dfetch can neither fetch it nor
    report it as a dependency. Removing it lets ``git submodule
    update``/``foreach`` proceed over the submodules that remain, instead of
    aborting the whole operation. Every stripped gitlink is re-staged on
    exit, so this leaves no lasting change -- safe to use even against a
    repository dfetch does not own, such as the user's own working
    directory during ``dfetch import``.
    """
    declared = declared_submodule_paths()
    removed = [(path, sha) for path, sha in _gitlink_entries() if path not in declared]
    for path, _sha in removed:
        logger.debug(
            "Gitlink '%s' has no '.gitmodules' entry; skipping it as a submodule",
            path,
        )
        run_on_cmdline(logger, ["git", "update-index", "--force-remove", "--", path])
    try:
        yield
    finally:
        for path, sha in removed:
            run_on_cmdline(
                logger,
                [
                    "git",
                    "update-index",
                    "--add",
                    "--cacheinfo",
                    f"160000,{sha},{path}",
                ],
            )


# ---------------------------------------------------------------------------
# Submodule URL/branch resolution
# ---------------------------------------------------------------------------


def get_submodule_urls(toplevel: str, origin_url: str) -> dict[str, str]:
    """Return {submodule name: absolute url} declared in <toplevel>/.gitmodules.

    Args:
        toplevel: Root directory of the repo whose .gitmodules to read.
        origin_url: This repo's own origin url, used to resolve relative
            (``../``) submodule urls to absolute ones.
    """
    result = run_on_cmdline(
        logger,
        ["git", "config", "--file", toplevel + "/.gitmodules", "--get-regexp", "url"],
    )
    return {
        str(match.group(1)): ensure_abs_url(origin_url, str(match.group(2)))
        for match in re.finditer(r"submodule\.(.*)\.url\s+(.*)", result.stdout.decode())
    }


def ensure_abs_url(root_url: str, rel_url: str) -> str:
    """Make sure the given url is an absolute url."""
    if not rel_url.startswith("../"):
        return rel_url

    new_root_url = root_url.split("/")
    new_rel_url = rel_url.split("/")
    for elt in new_rel_url.copy():
        if elt != "..":
            break

        new_root_url.pop()
        new_rel_url.pop(0)

    return "/".join(new_root_url + new_rel_url)


# ---------------------------------------------------------------------------
# src/ignore filtering of a fetched submodule tree
# ---------------------------------------------------------------------------


def apply_src_and_ignore(
    remote: str,
    src: str | None,
    ignore: Sequence[str] | None,
    submodules: list[Submodule],
) -> list[Submodule]:
    """Apply src filter and ignore patterns, returning surviving submodules."""
    if src:
        submodules = filter_submodules_by_src(remote, src, submodules)

    for ignore_path in ignore or []:
        paths = [
            p
            for p in glob.glob(ignore_path)
            if not (os.path.isfile(p) and is_license_file(os.path.basename(p)))
        ]
        safe_rm(paths, within=".")

    return [s for s in submodules if os.path.exists(s.path)]


def filter_submodules_by_src(
    remote: str, src: str, submodules: list[Submodule]
) -> list[Submodule]:
    """Keep only submodules within *src*, remove others, then promote *src* to root."""
    within_src = []
    to_remove: set[str] = set()
    for submodule in submodules:
        if submodule.path == src:
            # Submodule IS the src directory itself; keep it in-scope without
            # altering its path and let move_src_folder_up handle promotion.
            within_src.append(submodule)
            continue
        new_path = strip_glob_prefix(submodule.path, src)
        if new_path != submodule.path:
            submodule.path = new_path
            within_src.append(submodule)
        else:
            if Path(src).is_relative_to(Path(submodule.path)):
                continue
            to_remove.add(submodule.path)
    for path in to_remove:
        safe_rm(path, within=".")
    remove_empty_parents(to_remove)
    move_src_folder_up(remote, src)
    return within_src


def remove_empty_parents(paths: set[str]) -> None:
    """Remove empty ancestor directories left after removing out-of-scope submodule dirs.

    git submodule update may create a parent directory for a submodule even when
    sparse-checkout excludes it; after safe_rm removes the exact submodule path the
    parent can be left as an empty directory.  os.rmdir is used because it is atomic
    and raises OSError when the directory is not empty, which stops the upward walk.
    """
    for path in paths:
        parent = Path(path).parent
        while parent != Path("."):
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent


def _collect_safe_paths(src: str, repo_root: Path, remote: str) -> list[str]:
    """Return glob-matched paths for *src* that are within *repo_root*.

    Paths that escape the repo root are skipped with a warning.
    """
    safe_matched, escaped = glob_within_root(src, repo_root)
    for p in escaped:
        logger.warning(
            f"The 'src:' filter '{src}' matched '{p}' outside the repo root"
            f" for '{remote}'; skipping"
        )
    return safe_matched


def _apply_move(chosen: Path, repo_root: Path, remote: str) -> None:
    """Move the contents of *chosen* to the repo root and remove the empty parent."""
    # Pre-remove git metadata at the root of *chosen* before promoting its contents.
    # When *chosen* is itself a cloned submodule it contains a .git file that would
    # collide with the parent repo's .git directory; the caller cleans these up
    # recursively after checkout anyway.
    for name in (METADATA_DIR, GIT_MODULES_FILE):
        safe_rm(chosen / name, within=chosen)
    try:
        move_directory_contents(str(chosen), ".")
    except FileNotFoundError:
        logger.warning(
            f"The 'src:' filter '{chosen}' didn't match any files from '{remote}'"
        )
        return
    parts = chosen.relative_to(repo_root).parts
    if parts:
        try:
            safe_rm(repo_root / parts[0], within=repo_root)
        except FileNotFoundError:
            logger.debug(
                f"Nothing left to remove at '{repo_root / parts[0]}' after moving '{chosen}' for '{remote}'"
            )


def move_src_folder_up(remote: str, src: str) -> None:
    """Move the files from the src folder into the root of the project.

    Args:
        remote (str): Name of the root
        src (str): Src folder to move up
    """
    if os.path.isabs(src):
        logger.warning(
            f"The 'src:' filter '{src}' is an absolute path; skipping for '{remote}'"
        )
        return

    repo_root = Path(os.getcwd()).resolve()
    safe_matched = _collect_safe_paths(src, repo_root, remote)

    if not safe_matched:
        logger.warning(
            f"The 'src:' filter '{src}' didn't match any files from '{remote}'"
        )
        return

    # Resolve to canonical absolute paths so downstream steps use stable paths
    # regardless of any '..' components in the original glob results.
    resolved_dirs = [Path(d).resolve() for d in unique_parent_dirs(safe_matched)]

    if len(resolved_dirs) > 1:
        display = resolved_dirs[0].relative_to(repo_root)
        logger.warning(
            f"The 'src:' filter '{src}' matches multiple directories from '{remote}'. "
            f"Only considering files in '{display}'."
        )

    if resolved_dirs:
        _apply_move(resolved_dirs[0], repo_root, remote)
