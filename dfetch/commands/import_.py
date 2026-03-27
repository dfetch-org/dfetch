"""*Dfetch* can convert an existing project's dependencies to a dfetch manifest.

Dfetch will look for all submodules, externals, or third-party dependency
declarations in the current project and generate a manifest with the current
versions of the repositories.

After importing, remove the original dependency declarations and let dfetch
manage vendoring by running :ref:`dfetch update <update>`.

Migrating from git submodules
=============================

* Make sure your repository is up-to-date.
* Make sure your submodules are up-to-date (``git submodules update --init``).
* Generate a manifest using :ref:`dfetch import<import>`.
* Remove all git submodules (see `How do I remove a submodule
  <https://stackoverflow.com/questions/1260748/>`_ ).
* Download all your projects using :ref:`dfetch update<update>`.
* Commit your projects as part of your project.

.. scenario-include:: ../features/import-from-git.feature

Switching branches
~~~~~~~~~~~~~~~~~~
After importing submodules into a manifest within a branch, you might encounter
difficulties when switching branches.  If one branch has submodules located
where your *DFetched* project dependencies should be, or vice versa.
In both situations below, assume a branch ``feature/use-dfetch`` with a
manifest and ``master`` with the original submodules in their place.

Switching from branch with submodules to branch with manifest
-------------------------------------------------------------
When switching from branch with submodules to one without, git will warn that
the *Dfetched* project dependencies will overwrite the submodule that is
currently in the same location.

.. code-block:: console

    $ git checkout feature/use-dfetch
    error: The following untracked working tree files would be overwritten by checkout:
        MySubmodule/somefile.c
        MySubmodule/someotherfile.c

However, ``git status`` will show nothing:

.. code-block:: console

    $ git status
    On branch master
    Your branch is up to date with 'origin/master'.

    nothing to commit, working tree clean

To overcome this, remove the submodule folder and checkout branch
``feature/use-dfetch``:

.. code-block:: console

    $ rm -rf MySubmodule
    $ git checkout feature/use-dfetch

Switching from branch with manifest to branch with submodules
-------------------------------------------------------------
This situation gives no problem, *but* the submodules are gone and need to be
initialized again.  To solve this:

.. code-block:: console

    $ git checkout master
    $ git submodule update --init
    Submodule path 'MySubmodule': checked out '08f95e01b297d8b8c1c9101bde58e75cd4d428ce'


Migrating from SVN externals
============================

* Make sure your repository is up-to-date.
* Generate a manifest using :ref:`dfetch import<import>`.
* Remove all svn externals (see `How do I remove svn::externals
  <https://stackoverflow.com/questions/1044649/>`_ ).
* Download all your projects using :ref:`dfetch update<update>`.
* Commit your projects as part of your project.

.. scenario-include:: ../features/import-from-svn.feature

Migrating from CMake FetchContent / ExternalProject
====================================================

* Make sure your repository is up-to-date.
* Generate a manifest using ``dfetch import --detect cmake``.
* Remove or disable the CMake dependency declarations.
* Download all your projects using :ref:`dfetch update<update>`.
* Commit your projects as part of your project.

.. scenario-include:: ../features/import-from-cmake.feature

"""

import argparse
import os
import re
from collections.abc import Sequence
from itertools import combinations
from pathlib import Path

import dfetch.commands.command
from dfetch import DEFAULT_MANIFEST_NAME
from dfetch.commands import detectors
from dfetch.log import get_logger
from dfetch.manifest.manifest import Manifest
from dfetch.manifest.project import ProjectEntry
from dfetch.manifest.remote import Remote
from dfetch.project import determine_superproject_vcs

logger = get_logger(__name__)

_AVAILABLE_DETECTORS = detectors.names()


class Import(dfetch.commands.command.Command):
    """Generate manifest from existing submodules, externals, or declared dependencies.

    Look for submodules in a git project, externals in an svn project, or use
    ``--detect`` to also scan third-party dependency declaration files (e.g.
    CMake FetchContent).  All found dependencies are written to a manifest.
    """

    @staticmethod
    def create_menu(subparsers: dfetch.commands.command.SubparserActionType) -> None:
        """Add the parser menu for this action."""
        parser = dfetch.commands.command.Command.parser(subparsers, Import)
        parser.add_argument(
            "--detect",
            nargs="+",
            choices=_AVAILABLE_DETECTORS,
            metavar="SOURCE",
            default=[],
            help=(
                "Additional project-file formats to scan for dependencies. "
                f"Available sources: {', '.join(_AVAILABLE_DETECTORS)}. "
                "May be repeated or combined, e.g. ``--detect cmake``."
            ),
        )
        parser.add_argument(
            "--clean-sources",
            action="store_true",
            default=False,
            help=(
                "After detecting, comment out or remove the found declarations "
                "from their source files.  Requires ``--detect``.  "
                "Support depends on the chosen SOURCE."
            ),
        )

    def __call__(self, args: argparse.Namespace) -> None:
        """Perform the import."""
        projects = list(determine_superproject_vcs(".").import_projects())

        detect_names: list[str] = getattr(args, "detect", []) or []
        for detector_name in detect_names:
            projects.extend(detectors.get(detector_name).detect(Path(".")))

        if not projects:
            raise RuntimeError(f"No projects found in {os.getcwd()}!")

        remotes = _create_remotes(projects)

        for project in projects:
            # Prefer the longest matching remote URL to minimise the repo-path.
            # e.g. prefer git@git.github.com:some-org over git@git.github.com
            for remote in reversed(sorted(remotes, key=lambda r: len(r.url))):
                if project.remote_url.startswith(remote.url):
                    project.set_remote(remote)
                    break

        if getattr(args, "clean_sources", False):
            _clean_detected_sources(detect_names)

        manifest = Manifest(
            {"version": "0.0", "remotes": remotes, "projects": projects}
        )
        manifest.dump(DEFAULT_MANIFEST_NAME)
        logger.info(f"Created manifest ({DEFAULT_MANIFEST_NAME}) in {os.getcwd()}")


def _clean_detected_sources(detect_names: list[str]) -> None:
    """Invoke clean_sources on each detector, logging a warning if unsupported.

    Args:
        detect_names: List of detector names whose sources should be cleaned.
    """
    for name in detect_names:
        detector = detectors.get(name)
        if detector.supports_clean_sources:
            detector.clean_sources(Path("."))
        else:
            logger.warning(
                f"--clean-sources is not yet supported for '{name}'; skipping."
            )


def _create_remotes(projects: Sequence[ProjectEntry]) -> Sequence[Remote]:
    """Create a list of Remotes optimised for the fewest entries and smallest manifest.

    Args:
        projects: A list of projects.

    Returns:
        A list of remotes.
    """
    return [
        Remote(
            {
                "name": _generate_remote_name(remote),
                "url-base": remote,
                "default": False,
            }
        )
        for remote in _determine_best_remotes(
            {project.remote_url for project in projects}
        )
    ]


def _generate_remote_name(remote_url: str) -> str:
    """Generate a kind-of human readable name based on a url.

    Args:
        remote_url: URL to derive a name from.

    Returns:
        A slug-style name derived from the URL.
    """
    filtered = (
        re.sub(r"[./\\@:\^]", "-", remote_url).replace("https", "").replace("http", "")
    )
    return re.sub(r"[-]{2,}", "-", filtered).strip("-")


def _determine_best_remotes(projects_urls: set[str]) -> tuple[str, ...]:
    """Determine the smallest set of remotes that covers all project URLs.

    Args:
        projects_urls: A set of project URLs.

    Returns:
        A tuple of remote URL strings.
    """
    max_remote_length = 50
    max_remotes = 5

    potential_remotes: set[str] = set()
    for url in projects_urls:
        potential_remotes.add(url[:max_remote_length].rsplit("/", maxsplit=1)[0])
        potential_remotes.add(url[:max_remote_length].rsplit("/", maxsplit=2)[0])
        potential_remotes.add(url[:max_remote_length].rsplit(":", maxsplit=1)[0])

    potential_remotes -= {"http", "https"}

    solutions: list[tuple[int, tuple[str, ...]]] = []
    for i in range(min(len(potential_remotes), max_remotes)):
        for solution in combinations(potential_remotes, i):
            solutions.append(
                (_calculate_solution_score(solution, projects_urls), solution)
            )

    return min(solutions)[1]


def _calculate_solution_score(
    solution: tuple[str, ...], projects_urls: set[str]
) -> int:
    """Calculate a score for the given remote solution (lower is better).

    Args:
        solution: A candidate set of remote URL strings.
        projects_urls: The full set of project URLs to cover.

    Returns:
        An integer score; lower is a better solution.
    """
    score = len(solution)
    for url in projects_urls:
        minimum = len(url)
        for remote in solution:
            if url.startswith(remote):
                minimum = min(minimum, len(url) - len(remote))
        score += minimum
    return score
