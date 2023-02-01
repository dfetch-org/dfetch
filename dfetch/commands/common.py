"""Module for common command operations."""
import os
from typing import List

import yaml

from dfetch.log import get_logger
from dfetch.manifest.manifest import Manifest, get_childmanifests
from dfetch.manifest.project import ProjectEntry

logger = get_logger(__name__)


def check_child_manifests(manifest: Manifest, project: ProjectEntry, path: str) -> None:
    """Check for child manifests within a project.

    Args:
        manifest (dfetch.manifest.manifest.Manifest): The parent manifest with projects.
        project (ProjectEntry): The parent project.
        path (str): The path of the parent manifest.
    """
    for (
        childmanifest,
        childmanifest_path,
    ) in get_childmanifests(skip=[path]):
        recommendations: List[ProjectEntry] = []
        for childproject in childmanifest.projects:
            if childproject.remote_url not in [
                project.remote_url for project in manifest.projects
            ]:
                recommendations.append(childproject.as_recommendation())

        if recommendations:
            childmanifest_path = os.path.relpath(
                childmanifest_path, start=os.path.dirname(path)
            ).replace("\\", "/")
            _make_recommendation(project, recommendations, childmanifest_path)


def _make_recommendation(
    project: ProjectEntry, recommendations: List[ProjectEntry], childmanifest_path: str
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
