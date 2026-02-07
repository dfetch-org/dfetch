"""All Project related items."""

import os
import pathlib
from typing import Union

import dfetch.manifest.project
from dfetch.log import get_logger
from dfetch.manifest.parse import find_manifest, parse
from dfetch.project.gitsubproject import GitSubProject
from dfetch.project.gitsuperproject import GitSuperProject
from dfetch.project.subproject import SubProject
from dfetch.project.superproject import NoVcsSuperProject, SuperProject
from dfetch.project.svnsubproject import SvnSubProject
from dfetch.project.svnsuperproject import SvnSuperProject
from dfetch.util.util import resolve_absolute_path

SUPPORTED_SUBPROJECT_TYPES = [GitSubProject, SvnSubProject]
SUPPORTED_SUPERPROJECT_TYPES = [GitSuperProject, SvnSuperProject]

logger = get_logger(__name__)


def create_sub_project(
    project_entry: dfetch.manifest.project.ProjectEntry,
) -> SubProject:
    """Create a new SubProject based on a project from the manifest."""
    for project_type in SUPPORTED_SUBPROJECT_TYPES:
        if project_type.NAME == project_entry.vcs:
            return project_type(project_entry)

    for project_type in SUPPORTED_SUBPROJECT_TYPES:
        project = project_type(project_entry)

        if project.check():
            return project
    raise RuntimeError("vcs type unsupported")


def create_super_project() -> SuperProject:
    """Create a SuperProject by looking for a manifest file."""
    logger.debug("Looking for manifest")
    manifest_path = find_manifest()

    logger.debug(f"Using manifest {manifest_path}")
    manifest = parse(manifest_path)
    root_directory = resolve_absolute_path(os.path.dirname(manifest.path))
    return determine_superproject_vcs(root_directory)(manifest, root_directory)


def determine_superproject_vcs(path: Union[str, pathlib.Path]) -> type[SuperProject]:
    """Determine correct VCS type of the superproject in the given path."""
    for project_type in SUPPORTED_SUPERPROJECT_TYPES:
        if project_type.check(path):
            return project_type

    return NoVcsSuperProject
