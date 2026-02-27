"""Module for common command operations."""

import os

import yaml

from dfetch.log import get_logger
from dfetch.manifest.manifest import Manifest
from dfetch.manifest.parse import get_submanifests
from dfetch.manifest.project import ProjectEntry

logger = get_logger(__name__)


def check_sub_manifests(manifest: Manifest, project: ProjectEntry) -> None:
    """Check for sub-manifests within a project.

    Args:
        manifest (dfetch.manifest.manifest.Manifest): The parent manifest with projects.
        project (ProjectEntry): The parent project.
    """
    manifest_remote_urls = {project.remote_url for project in manifest.projects}

    for submanifest in get_submanifests(skip=[manifest.path]):
        recommendations: list[ProjectEntry] = []
        for subproject in submanifest.projects:
            if subproject.remote_url not in manifest_remote_urls:
                recommendations.append(subproject.as_recommendation())

        if recommendations:
            submanifest_relpath = os.path.relpath(
                submanifest.path, start=os.path.dirname(manifest.path)
            ).replace("\\", "/")
            _make_recommendation(project, recommendations, submanifest_relpath)


def _make_recommendation(
    project: ProjectEntry, recommendations: list[ProjectEntry], submanifest_path: str
) -> None:
    """Make recommendations to the user.

    Args:
        project (ProjectEntry): The parent project.
        recommendations (List[ProjectEntry]): List of recommendations
        submanifest_path (str): Path to the source of recommendations
    """
    recommendation_json = yaml.dump(
        [proj.as_yaml() for proj in recommendations],
        indent=4,
        sort_keys=False,
    )
    logger.print_warning_line(
        project.name,
        "\n".join(
            [
                f'"{project.name}" depends on the following project(s) which are not part of your manifest:',
                f"(found in {submanifest_path})",
                "",
                recommendation_json,
                "",
            ]
        ),
    )
