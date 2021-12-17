""""Module for common command operations."""
import os
from typing import List

import yaml

import dfetch.commands.command
import dfetch.manifest.manifest
import dfetch.manifest.validate
import dfetch.project
from dfetch.log import get_logger
from dfetch.manifest.project import ProjectEntry

logger = get_logger(__name__)


def check_child_manifests(
    manifest: dfetch.manifest.manifest.Manifest, project: ProjectEntry, path: str
) -> None:

    recommendations: List[ProjectEntry] = []
    for (
        childmanifest,
        childmanifest_path,
    ) in dfetch.manifest.manifest.get_childmanifests(skip=[path]):
        for childproject in childmanifest.projects:

            if childproject.remote_url not in [
                project.remote_url for project in manifest.projects
            ]:
                recommendations.append(childproject.as_recommendation())

        if recommendations:
            rel_path = os.path.relpath(
                childmanifest_path, start=os.path.dirname(path)
            ).replace("\\", "/")
            logger.warning(
                "\n".join(
                    [
                        "",
                        f'"{project.name}" depends on the following project(s) '
                        "which are not part of your manifest:",
                        f"(found in {rel_path})",
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
