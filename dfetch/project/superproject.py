"""Super project abstraction.

This module provides the SuperProject class which represents the project that
contains the `dfetch.yaml` manifest file (the "super project"). It provides
helpers to query VCS information about that repository (for example whether
it's a git or svn repository).
"""

from __future__ import annotations

import os
import pathlib
from collections.abc import Sequence

from dfetch.log import get_logger
from dfetch.manifest.manifest import Manifest
from dfetch.manifest.parse import find_manifest, parse
from dfetch.manifest.project import ProjectEntry
from dfetch.project.git import GitSubProject
from dfetch.project.subproject import SubProject
from dfetch.project.svn import SvnSubProject
from dfetch.vcs.git import GitLocalRepo
from dfetch.vcs.svn import SvnRepo

logger = get_logger(__name__)


class SuperProject:
    """Representation of the project containing the manifest.

    A SuperProject is the repository/directory that contains the dfetch
    manifest file. It exposes helpers to determine whether that project is
    managed by git, svn, or is unversioned.
    """

    def __init__(self) -> None:
        """Create a SuperProject by looking for a manifest file."""
        logger.debug("Looking for manifest")
        manifest_path = find_manifest()

        logger.debug(f"Using manifest {manifest_path}")
        self._manifest = parse(manifest_path)
        self._root_directory = os.path.dirname(self._manifest.path)

    @property
    def root_directory(self) -> str:
        """Return the directory that contains the manifest file."""
        return self._root_directory

    @property
    def manifest(self) -> Manifest:
        """The manifest of the super project."""
        return self._manifest

    def get_sub_project(self, project: ProjectEntry) -> SubProject | None:
        """Get the subproject in the same vcs type as the superproject."""
        if GitLocalRepo(self.root_directory).is_git():
            return GitSubProject(project)
        if SvnRepo(self.root_directory).is_svn():
            return SvnSubProject(project)

        return None

    def ignored_files(self, path: str) -> Sequence[str]:
        """Return a list of files that can be ignored in a given path."""
        if (
            os.path.commonprefix((pathlib.Path(path).resolve(), self.root_directory))
            != self.root_directory
        ):
            raise RuntimeError(f"{path} not in superproject {self.root_directory}!")

        if GitLocalRepo(self.root_directory).is_git():
            return GitLocalRepo.ignored_files(path)
        if SvnRepo(self.root_directory).is_svn():
            return SvnRepo.ignored_files(path)

        return []
