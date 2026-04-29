"""All Project related items."""

import os
import pathlib

import dfetch.manifest.project
from dfetch.log import get_logger
from dfetch.manifest.manifest import Manifest
from dfetch.manifest.parse import find_manifest
from dfetch.project.archivesubproject import ArchiveFetcher
from dfetch.project.gitsubproject import GitFetcher
from dfetch.project.gitsuperproject import GitSuperProject
from dfetch.project.subproject import SubProject
from dfetch.project.superproject import NoVcsSuperProject, SuperProject
from dfetch.project.svnsubproject import SvnFetcher
from dfetch.project.svnsuperproject import SvnSuperProject
from dfetch.util.util import resolve_absolute_path

_AnyFetcherType = type[ArchiveFetcher] | type[GitFetcher] | type[SvnFetcher]
SUPPORTED_FETCHERS: list[_AnyFetcherType] = [ArchiveFetcher, GitFetcher, SvnFetcher]
SUPPORTED_SUPERPROJECT_TYPES = [GitSuperProject, SvnSuperProject]

# Backward-compatible alias used by environment.py and any external callers.
SUPPORTED_SUBPROJECT_TYPES = SUPPORTED_FETCHERS

logger = get_logger(__name__)


def create_sub_project(
    project_entry: dfetch.manifest.project.ProjectEntry,
) -> SubProject:
    """Create a SubProject by selecting the appropriate fetcher for *project_entry*."""
    for fetcher_type in SUPPORTED_FETCHERS:
        if fetcher_type.NAME == project_entry.vcs:
            return SubProject(project_entry, fetcher_type(project_entry.remote_url))

    for fetcher_type in SUPPORTED_FETCHERS:
        if fetcher_type.handles(project_entry.remote_url):
            return SubProject(project_entry, fetcher_type(project_entry.remote_url))

    raise RuntimeError("vcs type unsupported")


def create_super_project() -> SuperProject:
    """Create a SuperProject by looking for a manifest file."""
    logger.debug("Looking for manifest")
    manifest_path = find_manifest()

    logger.debug(f"Using manifest {manifest_path}")
    manifest = Manifest.from_file(manifest_path)
    root_directory = resolve_absolute_path(os.path.dirname(manifest.path))
    return determine_superproject_vcs(root_directory)(manifest, root_directory)


def determine_superproject_vcs(path: str | pathlib.Path) -> type[SuperProject]:
    """Determine correct VCS type of the superproject in the given path."""
    for project_type in SUPPORTED_SUPERPROJECT_TYPES:
        if project_type.check(path):
            return project_type

    return NoVcsSuperProject
