"""Detect and neutralize gitlinks with no matching .gitmodules entry.

Some repositories contain gitlinks (mode ``160000``) that have no matching
entry in ``.gitmodules`` -- for example an accidentally committed
``git worktree`` directory or nested checkout. Both ``git submodule update
--init --recursive`` and ``git submodule foreach`` abort outright as soon as
they encounter such a gitlink, even though dfetch has no URL to fetch it
from and nothing useful to report about it anyway.
"""

import os
import re

from dfetch.log import get_logger
from dfetch.util.cmdline import SubprocessCommandError, run_on_cmdline

GIT_MODULES_FILE = ".gitmodules"

logger = get_logger(__name__)


def gitlink_paths() -> list[str]:
    """List the paths of all gitlinks (mode 160000) in the current index."""
    result = run_on_cmdline(logger, ["git", "ls-files", "-s", "-z"])
    paths = []
    for entry in result.stdout.decode().split("\0"):
        if not entry:
            continue
        meta, _, path = entry.partition("\t")
        if meta.split()[0] == "160000":
            paths.append(path)
    return paths


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


def drop_orphan_gitlinks() -> None:
    """Strip gitlinks with no .gitmodules entry from the index.

    Such a gitlink has no declared URL, so dfetch can neither fetch it nor
    report it as a dependency. Removing it from the index leaves its
    directory (if checked out at all) as an empty placeholder and lets
    ``git submodule update``/``foreach`` proceed over the submodules that
    remain, instead of aborting the whole operation.
    """
    declared = declared_submodule_paths()
    for path in gitlink_paths():
        if path not in declared:
            logger.debug(
                "Gitlink '%s' has no '.gitmodules' entry; skipping it as a submodule",
                path,
            )
            run_on_cmdline(
                logger, ["git", "update-index", "--force-remove", "--", path]
            )
