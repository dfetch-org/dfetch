"""*Dfetch* can convert your git submodules based project to dfetch.

Dfetch will look for all submodules in the current project and generate
a manifest with the current versions of the repository.

After importing you will have to remove the submodules and you can let dfetch
update by running :ref:`dfetch update <update>`.
"""

import argparse
import logging
import os
import re
from itertools import permutations
from typing import List, Sequence, Set, Tuple

import dfetch.commands.command
from dfetch.manifest.manifest import Manifest
from dfetch.manifest.project import ProjectEntry
from dfetch.manifest.remote import Remote
from dfetch.project.git import GitRepo

logger = logging.getLogger(__name__)


class Import(dfetch.commands.command.Command):
    """Generate manifest from existing submodules.

    Look for submodules in a git project and create a manifest based on that.
    """

    @staticmethod
    def create_menu(subparsers: "argparse._SubParsersAction") -> None:
        """Add the parser menu for this action."""
        dfetch.commands.command.Command.parser(subparsers, Import)

    def __call__(self, _: argparse.Namespace) -> None:
        """Perform the import."""
        projects = _import_from_git()

        if not projects:
            raise RuntimeError(f"No submodules found in {os.getcwd()}!")

        remotes = _create_remotes(projects)

        for project in projects:
            # To choose the best match, prefer longest remote url.
            # e.g. Prefer git@git.github.com:some-org over git@git.github.com
            for remote in reversed(sorted(remotes, key=lambda remote: len(remote.url))):
                if project.remote_url.startswith(remote.url):
                    project.set_remote(remote)

        manifest = Manifest(
            {"version": "0.0", "remotes": remotes, "projects": projects}
        )

        manifest.dump("manifest.yaml")
        logger.info(f"Created manifest (manifest.yaml) in {os.getcwd()}")


def _import_from_git() -> Sequence[ProjectEntry]:
    projects: List[ProjectEntry] = []
    toplevel: str = ""
    for submodule in GitRepo.submodules(logger):
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
                "name": re.sub(r"[./\\@:]", "-", remote),
                "url-base": remote,
                "default": False,
            }
        )
        for remote in _determine_best_remotes(
            {project.remote_url for project in projects}
        )
    ]


def _determine_best_remotes(projects_urls: Set[str]) -> Tuple[str, ...]:
    """Determine the smallest amount of remotes, that cover the most urls.

    Args:
        projects_urls (Set[str]): A list of urls of projects.

    Returns:
        Tuple[str, ...]: A set of remote urls.
    """
    # Determine all possible remotes
    potential_remotes: Set[str] = set()
    for url in projects_urls:
        potential_remotes.add(url.rsplit("/", maxsplit=1)[0])
        potential_remotes.add(url.rsplit(":", maxsplit=1)[0])

    # For each permutation of any length, calculate the solution score
    solutions = []
    for i in range(len(potential_remotes)):
        for solution in permutations(potential_remotes, i):
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
