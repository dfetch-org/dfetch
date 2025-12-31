"""Module for common command operations."""

import os
from collections.abc import Sequence

import yaml

from dfetch.log import get_logger
from dfetch.manifest.manifest import Manifest, get_childmanifests
from dfetch.manifest.project import ProjectEntry
from dfetch.project.svn import SvnRepo
from dfetch.vcs.git import GitLocalRepo

logger = get_logger(__name__)


def check_child_manifests(manifest: Manifest, project: ProjectEntry) -> None:
    """Check for child manifests within a project.

    Args:
        manifest (dfetch.manifest.manifest.Manifest): The parent manifest with projects.
        project (ProjectEntry): The parent project.
    """
    for childmanifest in get_childmanifests(skip=[manifest.path]):
        recommendations: list[ProjectEntry] = []
        for childproject in childmanifest.projects:
            if childproject.remote_url not in [
                project.remote_url for project in manifest.projects
            ]:
                recommendations.append(childproject.as_recommendation())

        if recommendations:
            childmanifest_relpath = os.path.relpath(
                childmanifest.path, start=os.path.dirname(manifest.path)
            ).replace("\\", "/")
            _make_recommendation(project, recommendations, childmanifest_relpath)


def _make_recommendation(
    project: ProjectEntry, recommendations: list[ProjectEntry], childmanifest_path: str
) -> None:
    """Make recommendations to the user.

    Args:
        project (ProjectEntry): The parent project.
        recommendations (List[ProjectEntry]): List of recommendations
        childmanifest_path (str): Path to the source of recommendations
    """
    logger.warning(
        "\n".join(
            [
                "",
                f'"{project.name}" depends on the following project(s) '
                "which are not part of your manifest:",
                f"(found in {childmanifest_path})",
            ]
        )
    )

    recommendation_json = yaml.dump(
        [proj.as_yaml() for proj in recommendations],
        indent=4,
        sort_keys=False,
    )
    logger.warning("")
    for line in recommendation_json.splitlines():
        logger.warning(line)
    logger.warning("")


def files_to_ignore(path: str) -> Sequence[str]:
    """Return a list of files that can be ignored in a given path."""
    if GitLocalRepo().is_git():
        ignore_list = GitLocalRepo.ignored_files(path)
    elif SvnRepo.check_path():
        ignore_list = SvnRepo.ignored_files(path)
    else:
        ignore_list = []
    return ignore_list
