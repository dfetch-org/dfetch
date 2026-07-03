"""*Dfetch* can filter file paths based on whether *Dfetch* manages them.

Files fetched by *Dfetch* are plain files in your repository. This makes them easy
to use, but tools such as formatters and linters typically shouldn't touch them.
``dfetch filter`` tells you which paths are managed by *Dfetch*, so you can skip
them when running tools or guard them in a `pre-commit <https://pre-commit.com>`_ hook.

Without any paths it lists everything below the project destinations of the manifest:

.. code-block:: console

    $ dfetch filter
    third-party/mymodule
    third-party/mymodule/README.md

You can also pipe paths in (for example from ``find`` or ``git diff --name-only``);
only the paths managed by *Dfetch* are echoed back:

.. code-block:: console

    $ git diff --name-only | dfetch filter

With ``--not-dfetched`` the selection is inverted and only the paths *not* managed
by *Dfetch* are kept. Paths outside the directory of the manifest are always dropped,
preventing path traversal. Paths that don't exist are passed through untouched, so
options meant for a wrapped tool survive the filtering.

When a command is given, it is called with the filtered paths. When nothing is left
after filtering, the command isn't called at all. This makes it easy to run a tool
on your own files only:

.. code-block:: console

    $ dfetch filter --not-dfetched black src/main.py third-party/mymodule/module.py

Here ``black`` is called with ``src/main.py`` only, since *Dfetch* manages
``third-party/mymodule``. See :ref:`Guard vendored files <guard-vendored-files>`
for wiring this into pre-commit.

.. scenario-include:: ../features/filter-projects.feature

"""

import argparse
import os
import sys
from collections.abc import Iterator
from pathlib import Path

import dfetch.commands.command
from dfetch.log import get_logger
from dfetch.manifest.manifest import Manifest
from dfetch.manifest.parse import find_manifest
from dfetch.util.cmdline import run_on_cmdline_uncaptured
from dfetch.util.util import resolve_absolute_path

logger = get_logger(__name__)


class Filter(dfetch.commands.command.Command):
    """Filter file paths based on whether dfetch manages them.

    Keep only the paths inside a project destination of the manifest, or only the
    paths outside them with ``--not-dfetched``. Paths can be given as arguments or
    piped through stdin; without any paths the project destinations are listed.
    When a command is given, it is called with the filtered paths.
    """

    SILENT = True

    @staticmethod
    def create_menu(subparsers: dfetch.commands.command.SubparserActionType) -> None:
        """Add the parser menu for this action."""
        parser = dfetch.commands.command.Command.parser(subparsers, Filter)
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--dfetched",
            "-D",
            action="store_true",
            help="Keep only paths managed by dfetch (default).",
        )
        group.add_argument(
            "--not-dfetched",
            "-N",
            action="store_true",
            help="Keep only paths not managed by dfetch.",
        )
        parser.add_argument(
            "cmd",
            metavar="<cmd>",
            type=str,
            nargs="?",
            help="Command to call with the filtered paths",
        )
        parser.add_argument(
            "args",
            metavar="<args>",
            nargs=argparse.REMAINDER,
            help="Paths to filter and pass to the command (non-paths are passed through)",
        )

    def __call__(self, args: argparse.Namespace) -> None:
        """Perform the filter."""
        manifest = Manifest.from_file(find_manifest())
        root = resolve_absolute_path(os.path.dirname(manifest.path))
        project_dirs = {
            resolve_absolute_path(root / project.destination)
            for project in manifest.projects
        }
        keep_dfetched = not args.not_dfetched

        candidates = _gather_candidates(args)
        if candidates:
            filtered = _filter_candidates(candidates, root, project_dirs, keep_dfetched)
        else:
            filtered = sorted(
                os.path.relpath(path)
                for path in _walk_paths(root, project_dirs, keep_dfetched)
            )

        if not filtered:
            logger.debug("No paths left after filtering")
        elif args.cmd:
            run_on_cmdline_uncaptured(logger, [args.cmd] + filtered)
        else:
            print("\n".join(filtered))


def _gather_candidates(args: argparse.Namespace) -> list[str]:
    """Collect the paths to filter from the command line and stdin."""
    candidates: list[str] = list(args.args)
    if not sys.stdin.isatty():
        candidates.extend(stripped for line in sys.stdin if (stripped := line.strip()))
    return candidates


def _filter_candidates(
    candidates: list[str],
    root: Path,
    project_dirs: set[Path],
    keep_dfetched: bool,
) -> list[str]:
    """Filter the given paths, paths that don't exist are passed through untouched."""
    kept: list[str] = []
    for candidate in candidates:
        if not os.path.exists(candidate):
            kept.append(candidate)
            continue
        path = resolve_absolute_path(candidate)
        if not path.is_relative_to(root):
            logger.debug(f"Dropped {candidate}: outside {root}")
        elif _is_dfetched(path, project_dirs) == keep_dfetched:
            kept.append(candidate)
        else:
            logger.debug(f"Dropped {candidate}")
    return kept


def _is_dfetched(path: Path, project_dirs: set[Path]) -> bool:
    """Check whether a path is inside any of the project destinations."""
    return any(path.is_relative_to(project_dir) for project_dir in project_dirs)


def _walk_paths(
    root: Path, project_dirs: set[Path], keep_dfetched: bool
) -> Iterator[Path]:
    """Yield the dfetched (or non-dfetched) paths below the given root.

    Only the relevant directories are visited: for dfetched paths just the project
    destinations are walked, otherwise the project destinations are pruned from the walk.
    """
    if keep_dfetched:
        for project_dir in sorted(project_dirs):
            if project_dir.is_dir() and project_dir.is_relative_to(root):
                yield project_dir
                yield from _walk_tree(project_dir, set())
    else:
        yield from _walk_tree(root, project_dirs)


def _walk_tree(top: Path, pruned_dirs: set[Path]) -> Iterator[Path]:
    """Yield every path below top, skipping ``.git`` directories and the pruned directories."""
    for dirpath, dirnames, filenames in os.walk(top):
        current = Path(dirpath)
        dirnames[:] = [
            name
            for name in dirnames
            if name != ".git" and current / name not in pruned_dirs
        ]
        for name in dirnames:
            yield current / name
        for name in filenames:
            yield current / name
