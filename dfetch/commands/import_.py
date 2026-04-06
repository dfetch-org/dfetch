"""*Dfetch* can convert your Git submodules or SVN externals based project to Dfetch.

Dfetch will look for all submodules or externals in the current project and generate
a manifest with the current versions of the repository.

After importing, you will need to remove the submodules or externals, and then you can let Dfetch
update by running :ref:`dfetch update <update>`.

For full step-by-step migration instructions see :ref:`migration`.

"""

import argparse
import os
import re
from collections.abc import Sequence
from itertools import combinations

import yaml

import dfetch.commands.command
from dfetch import DEFAULT_MANIFEST_NAME
from dfetch.log import get_logger
from dfetch.manifest.manifest import Manifest
from dfetch.manifest.project import ProjectEntry
from dfetch.manifest.remote import Remote
from dfetch.project import determine_superproject_vcs

logger = get_logger(__name__)


class Import(dfetch.commands.command.Command):
    """Generate manifest from existing submodules or externals.

    Look for submodules in a git project or externals in a svn project
    and create a manifest based on that.
    """

    @staticmethod
    def create_menu(subparsers: dfetch.commands.command.SubparserActionType) -> None:
        """Add the parser menu for this action."""
        dfetch.commands.command.Command.parser(subparsers, Import)

    def __call__(self, _: argparse.Namespace) -> None:
        """Perform the import."""
        projects = determine_superproject_vcs(".").import_projects()

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

        manifest_data = {
            "manifest": {
                "version": "0.0",
                "remotes": [r.as_yaml() for r in remotes],
                "projects": [p.as_yaml() for p in projects],
            }
        }
        manifest = Manifest.from_yaml(yaml.dump(manifest_data, sort_keys=False))

        manifest.dump(DEFAULT_MANIFEST_NAME)
        logger.info(f"Created manifest ({DEFAULT_MANIFEST_NAME}) in {os.getcwd()}")


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


def _determine_best_remotes(projects_urls: set[str]) -> tuple[str, ...]:
    """Determine the smallest amount of remotes, that cover the most urls.

    Args:
        projects_urls (Set[str]): A list of urls of projects.

    Returns:
        Tuple[str, ...]: A set of remote urls.
    """
    max_remote_length = 50
    max_remotes = 5

    # Determine all possible remotes
    potential_remotes: set[str] = set()
    for url in projects_urls:
        potential_remotes.add(url[:max_remote_length].rsplit("/", maxsplit=1)[0])
        potential_remotes.add(url[:max_remote_length].rsplit("/", maxsplit=2)[0])
        potential_remotes.add(url[:max_remote_length].rsplit(":", maxsplit=1)[0])

    useless_potential = {"http", "https"}
    potential_remotes = potential_remotes - useless_potential

    # For each permutation of any length, calculate the solution score
    solutions: list[tuple[int, tuple[str, ...]]] = []
    for i in range(min(len(potential_remotes), max_remotes)):
        for solution in combinations(potential_remotes, i):
            score = _calculate_solution_score(solution, projects_urls)
            solutions += [(score, solution)]

    # Select the solution with the lowest score
    return min(solutions)[1]


def _calculate_solution_score(
    solution: tuple[str, ...], projects_urls: set[str]
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
