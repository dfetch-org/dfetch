"""*Dfetch* can convert your git submodules or svn externals based project to dfetch.

Dfetch will look for all submodules or externals in the current project and generate
a manifest with the current versions of the repository.

After importing you will have to remove the submodules or externals and you can let dfetch
update by running :ref:`dfetch update <update>`.

Migrating from git submodules
=============================

* Make sure your repository is up-to-date.
* Make sure your submodules are up-to-date (``git submodules update --init``).
* Generate a manifest using :ref:`dfetch import<import>`.
* Remove all git submodules (see `How do I remove a submodule <https://stackoverflow.com/questions/1260748/>`_ ).
* Download all your projects using :ref:`dfetch update<update>`.
* Commit your projects as part of your project.

Migrating from SVN externals
============================

* Make sure your repository is up-to-date.
* Generate a manifest using :ref:`dfetch import<import>`.
* Remove all svn externals (see `How do I remove svn::externals <https://stackoverflow.com/questions/1044649/>`_ ).
* Download all your projects using :ref:`dfetch update<update>`.
* Commit your projects as part of your project.

"""

import argparse
import os
import re
from itertools import combinations
from typing import List, Sequence, Set, Tuple

import dfetch.commands.command
from dfetch import DEFAULT_MANIFEST_NAME
from dfetch.log import get_logger
from dfetch.manifest.manifest import Manifest
from dfetch.manifest.project import ProjectEntry
from dfetch.manifest.remote import Remote
from dfetch.project.git import GitRepo
from dfetch.project.svn import SvnRepo

logger = get_logger(__name__)


class Import(dfetch.commands.command.Command):
    """Generate manifest from existing submodules or externals.

    Look for submodules in a git project or externals in a svn project
    and create a manifest based on that.
    """

    @staticmethod
    def create_menu(subparsers: "argparse._SubParsersAction") -> None:
        """Add the parser menu for this action."""
        dfetch.commands.command.Command.parser(subparsers, Import)

    def __call__(self, _: argparse.Namespace) -> None:
        """Perform the import."""
        projects = _import_projects()

        if not projects:
            raise RuntimeError(f"No submodules found in {os.getcwd()}!")

        remotes = _create_remotes(projects)

        for project in projects:
            # To choose the best match, prefer longest remote url.
            # e.g. Prefer git@git.github.com:some-org over git@git.github.com
            for remote in reversed(sorted(remotes, key=lambda remote: len(remote.url))):
                if project.remote_url.startswith(remote.url):
                    project.set_remote(remote)
                    break

        manifest = Manifest(
            {"version": "0.0", "remotes": remotes, "projects": projects}
        )

        manifest.dump(DEFAULT_MANIFEST_NAME)
        logger.info(f"Created manifest ({DEFAULT_MANIFEST_NAME}) in {os.getcwd()}")


def _import_projects() -> Sequence[ProjectEntry]:
    """Find out what type of VCS is used and import projects."""
    if GitRepo.check_path():
        projects = _import_from_git()
    elif SvnRepo.check_path():
        projects = _import_from_svn()
    else:
        raise RuntimeError(
            "Only git or SVN projects can be imported.",
            "Run this command within either a git or SVN repository",
        )
    return projects


def _import_from_svn() -> Sequence[ProjectEntry]:
    projects: List[ProjectEntry] = []

    for external in SvnRepo.externals():
        projects.append(
            ProjectEntry(
                {
                    "name": external.name,
                    "revision": external.revision,
                    "url": external.url,
                    "dst": external.path,
                    "branch": external.branch,
                    "src": external.src,
                }
            )
        )
        logger.info(f"Found {external.name}")

    return projects


def _import_from_git() -> Sequence[ProjectEntry]:
    projects: List[ProjectEntry] = []
    toplevel: str = ""
    for submodule in GitRepo.submodules():
        projects.append(
            ProjectEntry(
                {
                    "name": submodule.name,
                    "revision": submodule.sha,
                    "url": submodule.url,
                    "dst": submodule.path,
                    "branch": submodule.branch,
                }
            )
        )
        logger.info(f"Found {submodule.name}")

        if not toplevel:
            toplevel = submodule.toplevel
        elif toplevel != submodule.toplevel:
            raise RuntimeError(
                "Recursive submodules not (yet) supported. Check manifest!"
            )

    if os.path.realpath(toplevel) != os.getcwd():
        logger.warning(
            "\n".join(
                (
                    f'The toplevel directory is in "{toplevel}"',
                    f'"dfetch import" was called from "{os.getcwd()}"',
                    "All projects paths will be relative to the current directory dfetch is running!",
                )
            )
        )

    return projects


def _create_remotes(projects: Sequence[ProjectEntry]) -> Sequence[Remote]:
    """Create a list of Remotes optimized for least amount of entries and smallest manifest.

    Args:
        projects (List[ProjectEntry]): A list of projects.

    Returns:
        List[Remote]: A list of remotes.
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
    """Generate a kind-of human readable name based on a url."""
    filtered = (
        re.sub(r"[./\\@:\^]", "-", remote_url).replace("https", "").replace("http", "")
    )
    return re.sub(r"[-]{2,}", "-", filtered).strip("-")


def _determine_best_remotes(projects_urls: Set[str]) -> Tuple[str, ...]:
    """Determine the smallest amount of remotes, that cover the most urls.

    Args:
        projects_urls (Set[str]): A list of urls of projects.

    Returns:
        Tuple[str, ...]: A set of remote urls.
    """
    max_remote_length = 50
    max_remotes = 5

    # Determine all possible remotes
    potential_remotes: Set[str] = set()
    for url in projects_urls:
        potential_remotes.add(url[:max_remote_length].rsplit("/", maxsplit=1)[0])
        potential_remotes.add(url[:max_remote_length].rsplit("/", maxsplit=2)[0])
        potential_remotes.add(url[:max_remote_length].rsplit(":", maxsplit=1)[0])

    useless_potential = set(["http", "https"])
    potential_remotes = potential_remotes - useless_potential

    # For each permutation of any length, calculate the solution score
    solutions = []
    for i in range(min(len(potential_remotes), max_remotes)):
        for solution in combinations(potential_remotes, i):
            score = _calculate_solution_score(solution, projects_urls)
            solutions += [(score, solution)]

    # Select the solution with the lowest score
    return min(solutions)[1]


def _calculate_solution_score(
    solution: Tuple[str, ...], projects_urls: Set[str]
) -> int:
    """Calculate a score with the given solution.

    Args:
        solution (Tuple[str, ...]): A set of remote urls
        projects_urls (Set[str]): A set of projects urls

    Returns:
        int: Lower score is a better solution
    """
    # Less remotes, is better
    score = len(solution)

    # Shortest url for projects, is better
    for url in projects_urls:
        minimum = len(url)
        for remote in solution:
            if url.startswith(remote):
                minimum = min(minimum, len(url) - len(remote))
        score += minimum

    return score
